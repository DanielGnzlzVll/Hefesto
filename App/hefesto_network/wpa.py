import hashlib
import logging
import os
import re
import tempfile

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

WPA_FILE = r"/etc/wpa_supplicant/wpa_supplicant.conf"

REGEX_HEFESTO = re.compile(
    "##HEFESTO_WIFI(.*?)##HEFESTO_WIFI", re.MULTILINE | re.DOTALL
)
REGEX_HEX_PSK = re.compile(r"^[0-9a-fA-F]{64}$")

NETWORK_TEMPLATE = """##HEFESTO_WIFI
network={{
        ssid={}
        psk={}
        scan_ssid=1
}}
##HEFESTO_WIFI
"""


def validate_ssid(ssid):
    if not 1 <= len(ssid.encode("utf-8")) <= 32:
        raise ValidationError("El SSID debe tener entre 1 y 32 bytes.")
    if any(ord(c) < 32 or ord(c) == 127 for c in ssid):
        raise ValidationError("El SSID no puede tener caracteres de control.")


def validate_psk(key):
    if REGEX_HEX_PSK.match(key):
        return
    if not 8 <= len(key) <= 63 or any(not 32 <= ord(c) <= 126 for c in key):
        raise ValidationError(
            "La contraseña debe tener entre 8 y 63 caracteres ASCII "
            "imprimibles, o ser 64 caracteres hexadecimales."
        )


def derive_psk(ssid, key):
    """Equivalente a ``wpa_passphrase``: PBKDF2-HMAC-SHA1, 4096 iteraciones."""
    if REGEX_HEX_PSK.match(key):
        return key.lower()
    return hashlib.pbkdf2_hmac(
        "sha1", key.encode("ascii"), ssid.encode("utf-8"), 4096, 32
    ).hex()


def render_network(ssid, key):
    validate_ssid(ssid)
    validate_psk(key)
    return NETWORK_TEMPLATE.format(
        ssid.encode("utf-8").hex(), derive_psk(ssid, key)
    )


def atomic_write(path, content):
    directory = os.path.dirname(path)
    mode = os.stat(path).st_mode & 0o7777
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".hefesto-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    except BaseException:
        os.unlink(tmp_path)
        raise
    dir_fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def change_ssid_key(ssid, key, path=WPA_FILE):
    """Cambia/añade la red-wifi configurada, en la interface web,
    ala configuracion del OS.

    :raises ValidationError: si el SSID o la contraseña no son validos
    :raises OSError: si no se puede leer o escribir el archivo
    """
    new_content = render_network(ssid, key)
    with open(path, "r") as f:
        wpa_content = f.read()
    if not wpa_content:
        logger.warning("WPA no se encontro nada en %s", path)
    wpa_content_clean = REGEX_HEFESTO.sub("", wpa_content)
    atomic_write(path, wpa_content_clean + new_content)


def apply_wifi(wifi, path=WPA_FILE):
    if not wifi.wifi_ssid:
        logger.info("SSID vacio, no se configura el wifi")
        return
    logger.info("Configurando el wifi")
    change_ssid_key(str(wifi.wifi_ssid), str(wifi.password), path)
