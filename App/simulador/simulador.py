import json
import logging
import os
import time
import requests
import random
import gzip

import click
import coloredlogs

logger = logging.getLogger(__name__)
coloredlogs.install(
    level=getattr(logging, os.getenv("logLevel", "info").upper()),
    logger=logger,
    fmt="[%(levelname)s] - %(asctime)s - %(processName)s|%(funcName)s(%(lineno)s): %(message)s",  # noqa
)


def _sleep(intervalo):
    logger.info("Durmiendo...")
    with click.progressbar(list(range(intervalo))) as bar:
        for item in bar:
            time.sleep(1)


def get_data():
    """
    Obtiene datos a enviar.
    :return: diccionario con los datos de las variables
    :rtype: dict
    """
    data_list = []
    now = time.time()
    for inverter in range(2):
        for var in range(3):
            data = {}
            data["timestamp"] = now + random.randint(1, 10)
            data[
                "var_name"
            ] = f"NombreConsulta__{inverter}__NombreVariable{var}"
            data["value"] = now % 100
            data["plugin"] = "MODBUS"
            data["context"] = {
                "request": "NombreConsulta",
                "var_name": f"NombreVariable{var}",
                "device": f"{inverter}",
            }

            data_list.append(data)
    for inverter in range(2):
        data = {}
        data["timestamp"] = now + random.randint(1, 10)
        data["var_name"] = f"NombreConsulta__{inverter}__OtroNombreVariable"
        data["value"] = now % 100
        data["plugin"] = "MODBUS"
        data["context"] = {
            "request": "NombreConsulta",
            "var_name": "OtroNombreVariable",
            "device": f"{inverter}",
        }
        data_list.append(data)

    for inverter in range(3):
        data = {}
        data["timestamp"] = now + random.randint(1, 10)
        data["var_name"] = f"OtroNombreConsulta__{inverter}__NombreVariable"
        data["value"] = now % 100
        data["plugin"] = "MODBUS"
        data["context"] = {
            "request": "OtroNombreConsulta",
            "var_name": "NombreVariable",
            "device": f"{inverter}",
        }

        data_list.append(data)
    return {"TIMESERIES": data_list}


def transmit(data, config):
    """
    Transmite hacia el servidor que venga en config.
    :param data: diccionario con los datos a enviar
    :type data: dict
    :param config: configuracion a usar para enviar los datos
    :type config: dict
    :return: respuesta desde el servidor
    :rtype: dict
    """
    additional_headers = {
        "Content-Type": "application/json",
        "Authorization": config.get("sastoken"),
    }
    logger.info(f"ENVIANDO: {data}")
    data_json = json.dumps(data).encode()

    if config.get("gzip"):
        logger.info("Comprimiendo datos")
        data_json = gzip.compress(data_json)
        additional_headers["content-encoding"] = "gzip"
    response = requests.post(
        config.get("url"),
        data=data_json,
        headers=additional_headers,
        timeout=2,
    )

    return response


@click.command()
@click.option(
    "--url",
    default="https://MyIoTHub.azure-devices.net/devices/MiDevice/messages/events?api-version=2018-04-01",  # noqa
    prompt="Ingrese URL del dispositivo",
    help="URL donde el dispositivo debe enviar los datos.",
)
@click.option(
    "--SASToken",
    default="SharedAccessSignature sr=MyIoTHub.azure-devices.net%2Fdevices%2FMyIoTDevice&sig=gqitFLvPA9AghisfjsTYUSDFGF8cx8cBOXCXOfwwd3qT8E%3D&se=1560379444",  # noqa
    prompt="Ingrese la cadena SAS",
    help="Shared Access Signatures.",
)
@click.option("--HEFESTO_ID", help="ID unico usado en el cuerpo del mensaje.")
@click.option(
    "--tiempo_entre_envios", default=30, help="Periodo entre envios (s)."
)
@click.option(
    "--gzip/--no-gzip",
    help="Habilitar o no compresion del contenido.",
    default=False,
)
@click.option(
    "--log-level",
    default="INFO",
    help="Log level.",
    type=click.Choice(
        ["DEBUG", "INFO", "ERROR", "CRITICAL"], case_sensitive=False
    ),
)
@click.pass_context
def main(*args, **config):
    """
    Simula el envio de datos a un servidor HTTP(S), usando como contenido
    un documentos JSON con el formato ´HEFESTO´

    ejemplos

    ========

    - url: 'https://MyIoTHub.azure-devices.net/devices/MiDevice/messages/events?api-version=2018-04-01'  # noqa

    - SASToken: 'SharedAccessSignature sr=MyIoTHub.azure-devices.net%2Fdevices%2FMyIoTDevice&sig=gqitFLvPA9AghisfjsTYUSDFGF8cx8cBOXCXOfwwd3qT8E%3D&se=1560379444'  # noqa
    """

    logger.setLevel(getattr(logging, config.get("log-level", "info").upper()))
    while True:

        data_json = {"HEFESTO_ID": config.get("HEFESTO_ID", "hefesto_001")}

        timeseries = get_data()
        data_json.update(timeseries)

        response = None
        try:
            response = transmit(data_json, config)
            if response.status_code < 300:
                logger.info("Transmision ok.")
                logger.info(
                    "Codigo de la respuesta: {}".format(response.status_code)
                )
                logger.info(
                    "Cuerpo de la respuesta: {}".format(
                        getattr(response, "body", None)
                    )
                )
            else:
                logger.error(
                    "Transmision fallida {} - {}".format(
                        response.status_code, response.reason
                    )
                )
        except requests.exceptions.ReadTimeout:
            logger.error("El servidor no responde.")
        except Exception as e:  # noqa
            logger.error(f"Transmision fallida: {e}")
            logger.exception(e)
            _sleep(config.get("tiempo_entre_envios", 30))
        _sleep(config.get("tiempo_entre_envios", 30))


if __name__ == "__main__":
    main()
