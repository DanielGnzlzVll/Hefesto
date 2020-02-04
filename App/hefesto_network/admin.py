from django.contrib import admin

from solo.admin import SingletonModelAdmin

from . import models

# Register your models here.


@admin.register(models.Wifi)
class WifiAdmin(SingletonModelAdmin):
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
