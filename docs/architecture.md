# Architecture

Hefesto runs on a single edge device (typically a Raspberry Pi) as a set of Docker containers orchestrated by `docker-compose`. All state lives in one PostgreSQL database: configuration, acquired time series, scheduled tasks and logs.

## Component view

```mermaid
flowchart LR
    user([Operator browser])
    field[[Field devices<br/>Modbus RTU / TCP]]
    http[(HTTP server)]
    azure[(Azure IoT Hub)]
    wifi["/etc/wpa_supplicant (host)"]

    subgraph device[Edge device - docker-compose]
        nginx[web<br/>nginx:alpine<br/>port 80]
        webapp[webapp<br/>Django admin<br/>gunicorn :8000]
        processor[processor<br/>hefesto_processor]
        grafana[grafana<br/>:3000]
        postgres[(postgres<br/>hefestodb)]
        migrate[migrate<br/>one-shot]
    end

    user -->|/hefesto/| nginx
    user -->|/grafana/| nginx
    nginx --> webapp
    nginx --> grafana
    nginx -->|/hefesto/static/| static[(static volume)]

    webapp --> postgres
    webapp -->|Wi-Fi config| wifi
    processor --> postgres
    grafana --> postgres
    migrate -->|migrate + collectstatic| postgres
    migrate --> static

    processor <-->|serial / TCP 502| field
    processor -->|POST time series| http
    http -.->|instructions in response| processor
    processor -->|device-to-cloud| azure
    azure -.->|cloud-to-device| processor
```

| Service | Image | Role |
|---|---|---|
| `web` | `nginx:alpine` | Only service exposed on the host (port 80). Routes `/hefesto/` to `webapp`, `/grafana/` to `grafana`, serves `/hefesto/static/`, and redirects `/` to the admin. |
| `webapp` | `hefesto` (built from `App/`) | Django admin used to configure everything. Runs privileged with `/etc/wpa_supplicant` mounted so saving the Wi-Fi form reconfigures the host. |
| `processor` | `hefesto` | Runs `manage.py hefesto_processor`, the scheduler that executes every enabled `Task` (acquisition, transmission, housekeeping). Privileged to reach serial ports. |
| `migrate` | `hefesto` | One-shot job: `collectstatic` + `migrate` on every `up`. |
| `postgres` | `postgres:10.7-alpine` | Single source of truth. Data persisted in the `pgdata` volume. |
| `grafana` | `grafana/grafana:6.6.0` | Dashboards over the `Postgres` datasource provisioned from `grafana/provisioning`. |

Two Docker networks isolate traffic: `nginx_proxy` (web, webapp, grafana) and `postgres` (everything that talks to the database). The database is never exposed outside the device.

Every container mounts `./App` from the host, so a `git pull` on the device updates the code; `every_hour.sh` and `after_reboot.sh` do this from cron and restart or rebuild the containers when something changed.

## Software view

The Django project in `App/` is split into plugin apps around a small core.

```mermaid
flowchart TB
    Task[(Task)]
    hp["hefesto_processor<br/>TaskReconciler + APScheduler"]

    subgraph plugins[Plugin commands]
        direction LR
        modbus["hefesto_modbus<br/>modbus_daemon"]
        httpagent["hefesto_http_agent<br/>http_send_data"]
        azureapp["hefesto_azure_iothub<br/>azure_send_data / azure_get_data"]
    end

    subgraph core[hefesto_core]
        direction LR
        TimeSerie[(TimeSerie)]
        core_services["core_services<br/>get_data2send()<br/>process_message_from_server()"]
    end

    subgraph system[System apps, driven from the admin]
        direction LR
        network["hefesto_network<br/>Wifi"]
        logging["hefesto_logging<br/>Log"]
    end

    Task -->|enabled tasks| hp
    hp -->|runs on cron| modbus
    hp -->|runs on cron| httpagent
    hp -->|runs on cron| azureapp
    modbus -->|writes ModbusTimeSerie| TimeSerie
    httpagent --> core_services
    azureapp --> core_services
    core_services -->|reads / marks exported| TimeSerie
    core_services -.->|allowlisted updates| modbus
```

### Apps

| App | Responsibility | Main models | Commands |
|---|---|---|---|
| `hefesto_core` | Shared time series storage, task scheduler, device identity, server-instruction processing. | `TimeSerie`, `Task`, `DeviceConfiguration` | `hefesto_processor`, `delete_old_timeseries` |
| `hefesto_modbus` | Modbus RTU (serial) and TCP polling: builds frames, validates CRC/length, decodes registers, evaluates write expressions. | `Consulta`, `VariableLectura`, `VariableEscritura`, `ModbusTimeSerie` | `modbus_daemon`, `modbus_procesar_consultas` |
| `hefesto_http_agent` | Pushes unexported time series to an HTTPS endpoint (Basic Auth, custom headers, optional gzip). | `Client`, `Header` | `http_send_data` |
| `hefesto_azure_iothub` | Device-to-cloud messages and cloud-to-device polling against Azure IoT Hub REST API with SAS tokens. | `Client` | `azure_send_data`, `azure_get_data` |
| `hefesto_network` | Writes the Wi-Fi network into `wpa_supplicant.conf` atomically when the form is saved. | `Wifi` | `config_wifi` |
| `hefesto_logging` | Stores every `INFO`+ log record in the database so it is visible in the admin. | `Log` | `delete_old_logs` |

### Plugin contract

A plugin is a Django app added to `INSTALLED_APPS` that follows these conventions:

1. **Configuration** is exposed as models registered in the admin (singletons via `django-solo` for one-per-device settings).
2. **Work** is a management command. In `AppConfig.ready()` the app does `Task.objects.get_or_create(...)` with `hidden=True`, a `command` such as `python manage.py modbus_daemon` and a `cron_expression`. Hidden tasks are not shown in the admin task list.
3. **Acquired data** is written as `TimeSerie` rows (or a subclass through multi-table inheritance, like `ModbusTimeSerie`) with a unique `name`, a JSON `value`, the `plugin` label and a free-form `context`.
4. **Transmission** plugins call `core_services.get_data2send()`, which returns the newest 1000 unexported points, a callback that marks them as `exported` after a successful send, and the processor for instructions returned by the server.

### Task scheduling

```mermaid
sequenceDiagram
    participant P as hefesto_processor
    participant DB as postgres (Task)
    participant S as APScheduler
    participant C as manage.py command

    loop every --interval seconds (default 30)
        P->>DB: Task.objects.filter(enable=True)
        P->>S: add / replace / remove jobs whose (name, command, cron) changed
    end
    S->>C: run command in a subprocess on each cron tick (UTC)
    C-->>S: exit code, stderr logged on failure
```

The long-running plugin commands (`modbus_daemon`, `http_send_data`, `azure_*`) loop internally, and APScheduler does not start a new instance of a job while the previous run is still going. The per-minute cron therefore acts as a supervisor that restarts the loop if it exits or crashes.

## Data flow

```mermaid
sequenceDiagram
    participant F as Field device
    participant M as modbus_daemon
    participant DB as postgres
    participant T as http_send_data / azure_send_data
    participant S as Remote server
    participant G as Grafana

    M->>DB: Consulta due (habilitada, proximo_request < now)
    M->>F: request frame (fn 3/4 read, 6/16 write)
    F-->>M: response frame
    M->>M: check length / CRC, decode by tipo_dato + byte_order,<br/>apply (value * escala) + offset
    M->>DB: insert ModbusTimeSerie (exported=False)
    M->>DB: proximo_request = now + intervalo_muestreo
    G->>DB: SQL queries over hefesto_core_timeserie
    T->>DB: get_data2send() (newest 1000 unexported, sent in chronological order)
    T->>S: POST {"HEFESTO_ID": ..., "TIMESERIES": [...]}
    S-->>T: 2xx + optional {"models": {...}}
    T->>DB: mark sent points exported=True
    T->>DB: apply allowlisted instructions
```

### Transmitted payload

```json
{
  "HEFESTO_ID": "<DeviceConfiguration.hefesto_id or CPU serial>",
  "TIMESERIES": [
    {
      "timestamp": "2026-01-01 12:00:00+00:00",
      "var-name": "METER__1__VOLTAGE",
      "value": 120.5,
      "plugin": "MODBUS RTU/SERIAL",
      "context": {"request": "meter", "var_name": "voltage", "device": 1}
    }
  ]
}
```

### Server instructions

The HTTP response body (HTTPS only) or an Azure cloud-to-device message may carry instructions:

```json
{
  "models": {
    "update": [
      {
        "name": "hefesto_modbus.Consulta",
        "filter": {"nombre": "meter"},
        "fields": {"intervalo_muestreo": 60}
      }
    ],
    "clean": []
  }
}
```

`process_message_from_server()` only accepts the models, operations and fields listed in `settings.HEFESTO_SERVER_INSTRUCTIONS`. Core Django apps, logging, network, transmission clients and `Task` are always rejected. All instructions in a message are validated first and applied in a single transaction, so an invalid instruction applies nothing. For Azure, a processed message is completed, an invalid one is rejected and a transient database error abandons it for redelivery.

### Retention

| Data | Limit |
|---|---|
| `TimeSerie` | Newest 10,000 rows kept on every insert; `delete_old_timeseries` removes rows older than 30 days. |
| `Log` | Newest 5,000 rows kept on every insert; `delete_old_logs` removes rows older than 2 days. |

The `delete_old_*` commands are not scheduled by default; add them as tasks if needed (see [Tutorials](tutorials.md#schedule-a-custom-task)).

## Database model

All apps share the `hefestodb` PostgreSQL database. Singleton models (`DeviceConfiguration`, both `Client`s, `Wifi`, `Ethernet`) hold a single row.

```mermaid
erDiagram
    DeviceConfiguration {
        int id PK
        char hefesto_id
    }
    Task {
        int id PK
        char name
        char command
        char cron_expression
        bool enable
        bool hidden
        datetime created
        datetime updated
    }
    TimeSerie {
        int id PK
        datetime time
        char name
        json value
        char plugin
        json context
        bool exported
        datetime created
        datetime updated
    }
    ModbusTimeSerie {
        int timeserie_ptr_id PK, FK
        int variable_id FK
        int dev_id
        char request_raw
        char response_raw
        bool crc_ok
    }
    Consulta {
        int id PK
        char nombre
        bool habilitada
        char dispositivos
        int codigo_funcion
        int registro_inicio
        int numero_registros
        float tiempo_espera
        int intervalo_muestreo
        datetime proximo_request
        char tipo_conexion
        char puerto_serial
        int baudrate
        char numero_bytes
        char paridad
        char bit_parada
        char ip
        int puerto_tcp
    }
    VariableLectura {
        int id PK
        int consulta_id FK
        char nombre
        char tipo_dato
        int longitud_texto
        char byte_order
        int desplazamiento
        int cantidad
        float escala
        float offset
    }
    VariableEscritura {
        int id PK
        int consulta_id FK
        char nombre
        text expresion
        char tipo_dato
        char byte_order
    }
    HttpClient["hefesto_http_agent.Client"] {
        int id PK
        char url
        char username
        char password
        bool habilitado
        bool gzip_habilitado
        int tiempo_entre_envios
    }
    Header {
        int id PK
        int config_id FK
        text key
        text value
    }
    AzureClient["hefesto_azure_iothub.Client"] {
        int id PK
        text connection_string
        bool habilitado
        int tiempo_entre_envios
        int tiempo_entre_peticiones
        bool gzip_habilitado
    }
    Wifi {
        int id PK
        char interface
        char wifi_ssid
        char password
        char mode
        char ip_address
        char ip_mask
        char ip_gateway
        char ip_dns
    }
    Ethernet {
        int id PK
        char interface
        char mode
        char ip_address
        char ip_mask
        char ip_gateway
        char ip_dns
    }
    Log {
        int id PK
        datetime timestamp
        char modulo
        int nivel
        text mensaje
        text trace
    }
    TimeSerie ||--o| ModbusTimeSerie : "extends"
    Consulta ||--o{ VariableLectura : "reads"
    Consulta ||--o{ VariableEscritura : "writes"
    VariableLectura |o--o{ ModbusTimeSerie : "produces"
    HttpClient ||--o{ Header : "sends"
```
