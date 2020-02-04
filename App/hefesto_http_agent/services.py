import gzip
import json
import logging
import time

import requests

from . import models

logger = logging.getLogger(__name__)


def transmit(data, config):
    """
    Transmite hacia el servidor que venga en config.
    :param data: diccionario con los datos a enviar
    :type data: dict
    :param config: configuracion a usar para enviar los datos
    :type config: models.Client
    :return: respuesta desde el servidor
    :rtype: dict
    """

    additional_headers = {"Content-Type": "application/json"}
    data_json = json.dumps(data).encode()

    for header in config.header_set.all():
        additional_headers[header.key] = header.value

    if config.gzip_habilitado:
        data_json = gzip.compress(data_json)
        additional_headers["content-encoding"] = "gzip"

    if config.username != "":
        response = requests.post(
            config.url,
            auth=(config.username, config.password),
            data=data_json,
            headers=additional_headers,
            timeout=10,
        )
    else:
        response = requests.post(
            config.url, data=data_json, headers=additional_headers, timeout=10
        )

    logger.debug("request headers: {}".format(response.request.headers))
    logger.debug("request body: {}".format(response.request.body))

    return response


def send_data():
    from hefesto_core import core_services, core_utils

    config = models.Client.get_solo()
    while config.habilitado:
        config = models.Client.get_solo()
        payload = {"HEFESTO_ID": core_utils.get_serial()}

        (
            data,
            success_callback,
            messages_processor,
        ) = core_services.get_data2send()
        payload.update(data)

        response = None
        try:
            response = transmit(payload, config)
        except Exception as e:  # noqa
            logger.error("Transmision fallida")
            logger.debug(e)
            time.sleep(config.tiempo_entre_envios * 2)
            continue

        if response.status_code < 300:
            success_callback()
        else:
            logger.error(
                "Transmision fallida {} - {}".format(
                    response.status_code, response.reason
                )
            )
        try:
            messages_processor(response.json())
        except:  # noqa
            pass
        time.sleep(config.tiempo_entre_envios)
    time.sleep(60)
