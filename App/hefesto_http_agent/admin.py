from django.contrib import admin
from solo.admin import SingletonModelAdmin

from . import models


# Register your models here.
@admin.register(models.Client)
class HtteServerAdmin(SingletonModelAdmin):
    fields = (
        ("url", "habilitado"),
        ("tiempo_entre_envios",),
        ("username", "password"),
        ("gzip_habilitado"),
    )
