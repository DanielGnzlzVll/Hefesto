import logging

from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv4_address
from django.db import models

from solo.models import SingletonModel

logger = logging.getLogger(__name__)

# Create your models here.


class NetworkConfigMixin(SingletonModel):
    """
    NetworkConfigMixin configuracion generica de una interface tcp/ip

    sirve como punto de almacenamiento y configuracion por medio de
    la interface web de los parametros de redes.

    :param mode: modo de configuracion (DHCP o STATIC)
    :type mode: str
    :param ip_address: en modo STATIC, es la ipv4 a usar
    :type ip_address: str
    :param ip_mask: en modo STATIC, es la mascara de subred a usar
    :type ip_mask: str
    :param ip_gateway: en modo STATIC, es la puerta de enlace predeterminada
    :type ip_gateway: str
    :param ip_dns: en modo STATIC, es la el servidor dns para usar
    :type ip_dns: str
    """

    net_modes = (("dhcp", "dhcp"), ("static", "static"))
    mode = models.CharField(max_length=50, choices=net_modes, default="dhcp")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    ip_mask = models.GenericIPAddressField(null=True, blank=True)
    ip_gateway = models.GenericIPAddressField(null=True, blank=True)
    ip_dns = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        abstract = True

    def clean(self):
        """
        valida los errores al llamar save()

        verifica que cuando el modo de red sea STATIC,
        no se configuren parametros en blanco.

        :raises ValidationError: [description]
        """

        errors = {}

        if self.mode == "static":
            if self.ip_address is None or len(self.ip_address) < 7:
                errors["ip_address"] = "Campo no puede estar vacio"
            validate_ipv4_address(self.ip_address)
            if self.ip_mask is None:
                errors["ip_gateway"] = "Campo no puede estar vacio"
            if self.ip_gateway is None:
                errors["ip_gateway"] = "Campo no puede estar vacio"
        if len(errors) > 0:
            raise ValidationError(list(errors.values()))


interfaces = (
    ("wlan0", "wlan0"),
    ("wlan1", "wlan1"),
    ("eth0", "eth0"),
    ("eth1", "eth1"),
)


class Wifi(NetworkConfigMixin):
    """
    Wifi interface para configurar el wifi

    hereda NetworkConfigMixin y sirve como punto de configuracion del wifi

    :param interface: interface fisica a configurar
    :type interface: str
    :param wifi_ssid: ssid(nombre) de la red wifi a configurar
    :type wifi_ssid: str
    :param password: contraseña de la red
    :type password: str
    """

    interface = models.CharField(
        max_length=100, blank=True, choices=interfaces[:2], default="wlan0"
    )
    wifi_ssid = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "WIFI"


class Ethernet(NetworkConfigMixin):
    """
    Ethernet interface para configurar la red ethernet

    hereda NetworkConfigMixin y sirve como punto de configuracion del ethernet

    :param interface: interface fisica a configurar
    :type interface: str
    """

    interface = models.CharField(
        max_length=100, blank=True, choices=interfaces[2:], default="eth0"
    )

    class Meta:
        verbose_name = "ETHERNET"
