import logging
import re

from django.core.management.base import BaseCommand

from ... import models

logger = logging.getLogger(__name__)


HEFESTO_SEP = "##HEFESTO_WIFI"
WPA_FILE = r"/etc/wpa_supplicant/wpa_supplicant.conf"

REGEX_HEFESTO = re.compile(
    "##HEFESTO_WIFI(.*?)##HEFESTO_WIFI", re.MULTILINE | re.DOTALL
)


def change_ssid_key(ssid, key):
    """Cambia/añade la red-wifi configurada, en la interface web,
    ala configuracion del OS.

    :param ssid: nombre de la red
    :type ssid: str
    :param key: contraseña de la red
    :type key: str
    """

    wpa_content = ""
    try:
        with open(WPA_FILE, "r") as f:
            wpa_content = f.read()
    except:  # noqa: E722
        logger.error("NO EXISTE ARCHIVO WIFI")
        return None
    if wpa_content:
        logger.debug("WPA se encontro el siguiente contenido" + wpa_content)
    else:
        logger.error("WPA no se encontro nada")
    wpa_content_clean = REGEX_HEFESTO.sub("", wpa_content)
    new_content_template = """##HEFESTO_WIFI
network={{
        ssid="{}"
        psk="{}"
        scan_ssid=1
}}
##HEFESTO_WIFI
"""

    new_content = new_content_template.format(ssid, key)
    new_wpa = wpa_content_clean + new_content
    with open(WPA_FILE, "w") as f:
        f.write(new_wpa)


class Command(BaseCommand):
    """configura la red wifi"""

    def handle(self, *args, **options):
        Wifi = models.Wifi.get_solo()
        ssid = str(Wifi.wifi_ssid)
        key = str(Wifi.password)
        logger.info("Configurando el wifi")
        change_ssid_key(ssid, key)
