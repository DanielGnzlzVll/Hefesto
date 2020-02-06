import gzip
import json
import logging
import time
from base64 import b64decode, b64encode
from hashlib import sha256
from hmac import HMAC
from urllib import parse

import requests

from hefesto_core import core_services, core_utils

from . import models

logger = logging.getLogger(__name__)

HOST_NAME = "HostName"
SHARED_ACCESS_KEY_NAME = "SharedAccessKeyName"
SHARED_ACCESS_KEY = "SharedAccessKey"
SHARED_ACCESS_SIGNATURE = "SharedAccessSignature"
DEVICE_ID = "DeviceId"
MODULE_ID = "ModuleId"
GATEWAY_HOST_NAME = "GatewayHostName"

_valid_keys = [
    HOST_NAME,
    SHARED_ACCESS_KEY_NAME,
    SHARED_ACCESS_KEY,
    SHARED_ACCESS_SIGNATURE,
    DEVICE_ID,
    MODULE_ID,
    GATEWAY_HOST_NAME,
]


# https://github.com/Azure/azure-iot-sdk-python/blob/6a21a2dba49faa663109ad2c2a22d65f008501f9/azure-iot-device/azure/iot/device/common/connection_string.py#L32
def parse_connection_string(connection_string):
    cs_args = connection_string.split(";")
    d = dict(arg.split("=", 1) for arg in cs_args)
    if len(cs_args) != len(d):
        # various errors related to incorrect parsing - duplicate args, bad syntax, etc.  # noqa
        raise ValueError("Invalid Connection String - Unable to parse")
    if not all(key in _valid_keys for key in d.keys()):
        raise ValueError("Invalid Connection String - Invalid Key")
    return d


# https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-security
def generate_sas_token(uri, key, policy_name, expiry=3600):
    ttl = time.time() + expiry
    sign_key = "%s\n%d" % ((parse.quote_plus(uri)), int(ttl))
    signature = b64encode(
        HMAC(b64decode(key), sign_key.encode("utf-8"), sha256).digest()
    )  # noqa

    rawtoken = {"sr": uri, "sig": signature, "se": str(int(ttl))}

    if policy_name is not None:
        rawtoken["skn"] = policy_name

    return "SharedAccessSignature " + parse.urlencode(rawtoken)


def get_sas_token_from_connection_string(connection_string):
    conn = parse_connection_string(connection_string)
    uri = conn.get(HOST_NAME)
    uri += "/devices/"
    uri += conn.get(DEVICE_ID)
    token = generate_sas_token(uri, conn.get(SHARED_ACCESS_KEY), None)
    return token


def transmit(data, config):
    conn = parse_connection_string(config.connection_string)
    token = get_sas_token_from_connection_string(config.connection_string)
    iotHub = conn.get(HOST_NAME)
    deviceId = conn.get(DEVICE_ID)

    additional_headers = {
        "Content-Type": "application/json",
        "Authorization": token,
    }
    data_json = json.dumps(data).encode()
    if config.gzip_habilitado:
        data_json = gzip.compress(data_json)
        additional_headers["content-encoding"] = "gzip"
    uri = (
        f"https://{iotHub}/devices/{deviceId}/messages/events?"
        "api-version=2018-04-01"
    )

    response = requests.post(
        uri, data=data_json, headers=additional_headers, timeout=10,
    )

    logger.debug("request headers: {}".format(response.request.headers))
    logger.debug("request body: {}".format(response.request.body))

    return response


def send_data():
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


def get_data():
    config = models.Client.get_solo()
    while config.habilitado and config.connection_string:
        config = models.Client.get_solo()
        conn = parse_connection_string(config.connection_string)
        token = get_sas_token_from_connection_string(config.connection_string)
        iotHub = conn.get(HOST_NAME)
        deviceId = conn.get(DEVICE_ID)
        additional_headers = {"Authorization": token}
        try:
            uri = (
                f"https://{iotHub}/devices/{deviceId}/messages/deviceBound?"
                "api-version=2018-04-01"
            )
            response = requests.get(
                uri, headers=additional_headers, timeout=10,
            )
        except Exception as e:  # noqa
            logger.error("Solicitud de datos fallida")
            logger.debug(e)
            time.sleep(config.tiempo_entre_peticiones * 2)
            continue

        if response.status_code < 300:
            etag = response.headers.get("etag", "").replace('"', "")
            if etag:
                logger.info(f"Mensaje recibido: {etag}")
                logger.info(f"Cuerpo mensaje: {response.content}")
                reject = True
                try:
                    core_services.process_message_from_server(response.json())
                except:  # noqa
                    reject = False
                uri = (
                    f"https://{iotHub}/devices/{deviceId}/messages/"
                    f"deviceBound/{etag}?api-version=2018-04-01"
                )
                if reject:
                    uri += "&reject"
                try:
                    _ = requests.delete(
                        uri, headers=additional_headers, timeout=10,
                    )
                    if reject:
                        logger.info(f"Mensaje rechazado: {etag}")
                    else:
                        logger.info(f"Mensaje completado: {etag}")
                except:  # noqa
                    pass
        else:
            logger.error(
                "Solicitud de datos  fallida {} - {}".format(
                    response.status_code, response.reason
                )
            )
        time.sleep(config.tiempo_entre_peticiones)
    time.sleep(60)
