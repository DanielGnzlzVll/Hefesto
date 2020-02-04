from django.contrib import admin, auth
from django.conf import settings


from solo.admin import SingletonModelAdmin

from . import models


# Register your models here.
@admin.register(models.DeviceConfiguration)
class ConfigurationDevicesAdmin(SingletonModelAdmin):
    fields = ["hefesto_id"]


@admin.register(models.TimeSerie)
class TimeSerieAdmin(admin.ModelAdmin):
    list_display = ["time", "name", "value", "plugin", "exported", "context"]
    list_filter = ["name", "plugin", "exported"]


@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "command",
        "cron_expression",
        "enable",
        "created",
        "updated",
    ]
    list_filter = ["name", "enable"]
    fields = ["name", "command", "cron_expression", "enable"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(hidden=False)


admin.site.unregister(auth.models.User)
admin.site.unregister(auth.models.Group)

admin.site.site_header = "IoT Gateway Hefesto - " + settings.HARDWARE_SERIAL
admin.site.site_title = "Hefesto"
admin.site.index_title = "Hefesto"
# admin.site.site_url = None
