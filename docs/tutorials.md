# Tutorials

These walkthroughs cover the features available in the admin at `http://<device>/hefesto/admin/`. See [Architecture](architecture.md) for how the pieces fit together.

- [First start](#first-start)
- [Set the device identity](#set-the-device-identity)
- [Read a Modbus device](#read-a-modbus-device)
- [Write Modbus registers from an expression](#write-modbus-registers-from-an-expression)
- [Visualize data in Grafana](#visualize-data-in-grafana)
- [Send data to an HTTP server](#send-data-to-an-http-server)
- [Send data to Azure IoT Hub](#send-data-to-azure-iot-hub)
- [Control the device from the server](#control-the-device-from-the-server)
- [Configure Wi-Fi](#configure-wi-fi)
- [Schedule a custom task](#schedule-a-custom-task)
- [Troubleshoot with logs](#troubleshoot-with-logs)

## First start

1. Follow the [installation steps](../README.md#installation) and create `.env`.
2. Run `docker-compose up -d` and wait for the `migrate` container to exit.
3. Open `http://<device>/`, which redirects to the admin.
4. Log in with the user created by the initial migration (`admin` / `admin`) and change its password right away from the top-right menu.

## Set the device identity

Every payload sent to a server carries a `HEFESTO_ID`. By default it is the CPU serial of the device.

1. Go to **Hefesto_Core > Device configuration**.
2. Fill **Hefesto id** with a unique name (for example `plant-a-gateway-01`), or leave it blank to keep the CPU serial.

## Read a Modbus device

In this example, a power meter with slave id `1` on `/dev/ttyUSB0` exposes voltage as a `float32` at holding registers 0-1 and a device counter as a `uint16` at register 2.

1. Go to **Hefesto_Modbus > Consultas > Add**.
2. Fill the request:
   - **Nombre**: `meter`
   - **Dispositivos**: `1` (ranges such as `1-3, 5` poll several slaves with the same map)
   - **Codigo funcion**: `3` (read holding registers) or `4` (read input registers)
   - **Registro inicio**: `0`
   - **Numero registros**: `3` (each register is 2 bytes)
   - **Intervalo muestreo**: `60` seconds
   - **Tipo conexion**: `RTU/SERIAL`, with **Puerto serial** `/dev/ttyUSB0`, baudrate, data bits, parity and stop bits matching the meter. For Modbus TCP choose `TCP/TCP` and set **Ip** and **Puerto tcp** instead.
3. Click **Save and continue editing** so the variable tables are shown for the saved request.
4. Add the read variables:

   | Nombre | Tipo dato | Byte order | Desplazamiento | Cantidad | Escala | Offset |
   |---|---|---|---|---|---|---|
   | `voltage` | `float32` | `ABCD` | `0` | `1` | `1` | `0` |
   | `counter` | `uint16` | `AB` | `4` | `1` | `1` | `0` |

   - **Desplazamiento** is the byte offset inside the response data.
   - **Byte order** must have as many letters as the type has bytes (`AB` for 16 bits, `ABCD`/`CDAB`/... for 32 bits, `ABCDEFGH`/`HGFEDCBA` for 64 bits). Use `CDAB` for devices that swap words.
   - **Cantidad** `N` reads `N` consecutive values and stores them as `NAME__1` ... `NAME__N`.
   - The stored value is `(raw * escala) + offset`. For `ascii` values set **Longitud texto** to the number of characters instead.
5. Save. The `modbus_daemon` task picks up the request on its next pass.
6. To poll right away, select the request in the list and run the **Realizar las consulta seleccionada/s** action.
7. Check **Hefesto_Core > Time series**. Each value is stored with the name `<REQUEST>__<SLAVE>__<VARIABLE>` in upper case, for example `METER__1__VOLTAGE`.

Requests that fail CRC, length or id checks are skipped and logged (see [Troubleshoot with logs](#troubleshoot-with-logs)).

## Write Modbus registers from an expression

Function codes `6` (write single register) and `16` (write multiple registers) compute the values to write from Python expressions every time the request runs.

1. Create a request as above, with **Codigo funcion** `16`, **Registro inicio** at the first register to write, and **Numero registros** covering all written values.
2. Save and continue editing, then add write variables in order:

   | Nombre | Expresion | Tipo dato | Byte order |
   |---|---|---|---|
   | `setpoint` | `METER__1__VOLTAGE * 0.9` | `float32` | `ABCD` |
   | `heartbeat` | `int(now) % 65536` | `uint16` | `AB` |

   An expression can use:
   - the latest value of any time series by its name, for example `METER__1__VOLTAGE`,
   - `<NAME>_time`, the Unix timestamp of that latest value,
   - `now`, the current Unix timestamp,
   - `dev`, the slave id being written,
   - the `math` module.

   Values are packed in the order the variables were created. An expression that fails is skipped, so check that the written bytes still match **Numero registros**.

## Visualize data in Grafana

1. Open `http://<device>/grafana/` and log in (Grafana's default user is `admin` / `admin`; change it on first login).
2. Create a dashboard and add a panel. The `Postgres` datasource is provisioned and selected by default.
3. Switch the query editor to raw SQL and plot a variable:

   ```sql
   SELECT
     time AS "time",
     name AS metric,
     (value::text)::float AS value
   FROM hefesto_core_timeserie
   WHERE $__timeFilter(time)
     AND name = 'METER__1__VOLTAGE'
   ORDER BY 1
   ```

   Use `name LIKE 'METER__%'` to plot every variable of a request. Modbus-specific columns (`dev_id`, `request_raw`, `response_raw`, `crc_ok`) are in `hefesto_modbus_modbustimeserie`, joined on `timeserie_ptr_id = hefesto_core_timeserie.id`.

## Send data to an HTTP server

1. Go to **Hefesto_Http_Agent > HTTP CLIENT**.
2. Set **Url** to your endpoint; only `https://` URLs are accepted.
3. Optionally fill **Username** / **Password** for Basic Auth and add extra headers (for example an API key) in the headers table.
4. Choose **Tiempo entre envios** (seconds between posts) and whether to gzip the body.
5. Check **Habilitado** and save. The `http_send_data` task starts sending within a minute.

Each post contains up to 1000 points not yet exported; they are marked as exported only when the server answers with a status below 300. The body format is described in [Architecture](architecture.md#transmitted-payload).

## Send data to Azure IoT Hub

1. Register the device in your IoT Hub and copy its primary connection string (`HostName=...;DeviceId=...;SharedAccessKey=...`).
2. Go to **Hefesto_Azure_Iothub > AZURE IoTHub**.
3. Paste the **Connection string**.
4. Set **Tiempo entre envios** (device-to-cloud interval) and **Tiempo entre peticiones** (cloud-to-device polling interval, minimum 25 minutes).
5. Check **Habilitado** and save. The `azure_iothub_send_data` and `azure_iothub_get_data` tasks start within a minute.

## Control the device from the server

A server can change the device configuration by answering a data post (HTTP agent) or by sending an Azure cloud-to-device message with a body like:

```json
{
  "models": {
    "update": [
      {
        "name": "hefesto_modbus.Consulta",
        "filter": {"nombre": "meter"},
        "fields": {"intervalo_muestreo": 30, "habilitada": true}
      }
    ]
  }
}
```

Only what `HEFESTO_SERVER_INSTRUCTIONS` in `App/project/settings.py` allows is applied. Out of the box that is updating `habilitada` and `intervalo_muestreo` on Modbus requests. To allow more, extend the setting, for example:

```python
HEFESTO_SERVER_INSTRUCTIONS = {
    "hefesto_modbus.Consulta": {
        "update": ["habilitada", "intervalo_muestreo"],
        "clean": True,
    },
}
```

`filter` and `exclude` accept Django lookups on the model's own fields (for example `{"nombre__startswith": "meter"}`). If any instruction in a message is invalid, none are applied and the reason is logged.

## Configure Wi-Fi

1. Go to **Hefesto_Network > WIFI**.
2. Pick the **Interface** (`wlan0` or `wlan1`), enter the **Wifi ssid** and **Password** (8-63 printable ASCII characters, or a 64-character hex PSK).
3. Save. The network is written to `/etc/wpa_supplicant/wpa_supplicant.conf` on the host. If it cannot be applied, the admin shows an error and the form values are kept.

The same configuration can be re-applied from a shell with `docker-compose exec webapp python manage.py config_wifi`.

## Schedule a custom task

Any shell command can run on a cron schedule inside the `processor` container.

1. Go to **Hefesto_Core > Tasks > Add**.
2. Fill:
   - **Name**: `purge old data`
   - **Command**: `python manage.py delete_old_timeseries`
   - **Cron expression**: `0 3 * * *` (standard 5-field cron, evaluated in UTC)
   - **Enable**: checked
3. Save. The processor reloads tasks every 30 seconds, runs the command once immediately and then on schedule. Editing or disabling the task takes effect on the next reload.

Commands run from `/usr/src/hefesto` with the application's environment, so any `manage.py` command is available, for example `python manage.py delete_old_logs`. A non-zero exit code is logged with the command's stderr. Tasks registered by the plugins are hidden from this list.

## Troubleshoot with logs

- **Hefesto_Logging > Logging** in the admin lists every `INFO` and higher record from the web app and all tasks, filterable by level and module, with the traceback when there is one.
- The same records go to the container output: `docker-compose logs -f processor` (acquisition and transmission) or `docker-compose logs -f webapp` (admin).
- **Hefesto_Core > Time series** shows each stored point, its `plugin`, `context` and whether it has been `exported`.
