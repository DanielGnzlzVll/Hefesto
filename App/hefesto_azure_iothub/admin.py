from django.contrib import admin
from solo.admin import SingletonModelAdmin

from . import models


# Register your models here.
@admin.register(models.Client)
class IoTHubAdmin(SingletonModelAdmin):
    fields = (
        ("connection_string", "habilitado"),
        ("tiempo_entre_envios", "tiempo_entre_peticiones"),
        ("gzip_habilitado", ),
    )
