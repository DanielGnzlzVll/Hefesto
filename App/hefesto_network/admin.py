import logging

from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from solo.admin import SingletonModelAdmin

from . import models, wpa

logger = logging.getLogger(__name__)

# Register your models here.


@admin.register(models.Wifi)
class WifiAdmin(SingletonModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            wpa.apply_wifi(obj)
        except (OSError, ValidationError) as e:
            logger.exception("No se pudo configurar el wifi")
            messages.error(
                request,
                "Se guardo la configuracion pero no se pudo aplicar "
                "al sistema: {}".format(e),
            )

    fieldsets = (
        ("BASIC", {"fields": (("interface", "wifi_ssid", "password"))}),
        # (
        #     "ADVANCED",
        #     {
        #         "fields": (
        #             "mode",
        #             ("ip_address", "ip_mask", "ip_gateway", "ip_dns"),
        #         )
        #     },
        # ),
    )


# @admin.register(models.Ethernet)
class EthernetAdmin(SingletonModelAdmin):
    fieldsets = (
        (
            "BASIC",
            {
                "fields": (
                    ("interface", "mode"),
                    ("ip_address", "ip_mask", "ip_gateway", "ip_dns"),
                )
            },
        ),
    )
