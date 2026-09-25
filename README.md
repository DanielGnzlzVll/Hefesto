# Hefesto
Hefesto is data acquisition software for high-level edge-computing devices.

It provides the foundation and graphical interface for end users who want to acquire data from sensors, equipment, or external information systems that support industrial protocols such as [Modbus](http://www.modbus.org/) (RTU, TCP, or ASCII), DLMS, HTTP, MQTT, among others.

It has a modular architecture that can be extended through plugins (Django apps) of the following types:

* Data acquisition for each protocol.
* Rules that take actions.
* Actions that are interpreted according to each protocol.

It uses [Grafana](https://grafana.com/) as its visualization tool.

## Documentation

* [Architecture](docs/architecture.md): containers, Django apps, task scheduling and data flow.
* [Tutorials](docs/tutorials.md): step-by-step guides for every feature.

## To do:

1. Write the documentation
1. Write tests
1. Image/Logo
1. Roadmap
    1. Meta requests in Hefesto_modbus
    1. Calculation engine
    1. Plugins
        1. Inputs
            1. Serial regex
            1. MQTT consumer
        1. Outputs
            1. Rules and commands
        1. Transmission
            1. MQTT
            1. OPC



# Installation
## Requirements
### Docker
[Get Docker](https://docs.docker.com/install/)
#### Debian/Ubuntu/Raspbian
```bash
sudo apt install docker
sudo systemctl start docker
```

#### Fedora/Redhat/centOS
```bash
sudo yum install docker
sudo systemctl start docker
```
### Docker-compose
```bash
sudo pip install docker-compose
```
## Download
```bash
git clone https://github.com/DanielGnzlzVll/Hefesto
cd Hefesto
```
## Environment variables
Create a `.env` file (not versioned) from `.env.example`, with a unique password per device:
```bash
echo "HEFESTO_DB_PASSWORD=$(openssl rand -hex 24)" > .env
```

| Variable | Required | Description |
|---|---|---|
| `HEFESTO_DB_PASSWORD` | Yes | PostgreSQL password, used by `postgres`, `grafana`, `migrate`, `webapp` and `processor`. The application does not start without it. |
| `HEFESTO_DB` | No | Database name (defaults to `hefestodb`). |
| `HEFESTO_DB_USER` | No | Database user (defaults to `hefesto`). |
| `HEFESTO_DB_HOST` | No | Database host (defaults to `postgres`). |
| `HEFESTO_DB_PORT` | No | Database port. |
| `DJANGO_SECRET_KEY` | No | Django secret key (defaults to a random one generated on each start). |
| `DJANGO_ALLOWED_HOSTS` | No | Comma-separated allowed hosts (defaults to `localhost,127.0.0.1,hefesto,hefesto.local,192.168.1.212,192.168.137.212`). Add the IP or hostname used to reach the device. |
| `DJANGO_DEBUG` | No | `1` to enable Django debug mode (off by default). |

`POSTGRES_PASSWORD` only applies when the `pgdata18` volume is created. To change the password on an already deployed device:
```bash
docker-compose exec postgres psql -U hefesto -d hefestodb -c "ALTER USER hefesto WITH PASSWORD '<new>';"
```
then update `HEFESTO_DB_PASSWORD` in `.env` and run `docker-compose up -d`.

## Start
```bash
docker-compose up
```


### Configuration
Go to the [Configuration](http://localhost/hefesto/admin/) page.

### Database structure:

See the [database model](docs/architecture.md#database-model).

## Bugs
Report any bug by email or open an [Issue!](https://github.com/DanielGnzlzVll/Hefesto/issues/new)
[jodgonzalezvi@unal.edu.co](mailto:jodgonzalezvi@unal.edu.co?subject=HefestoBug)
