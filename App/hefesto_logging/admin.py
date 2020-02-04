import logging

from django.contrib import admin
from django.utils.html import format_html

from . import models

logger = logging.getLogger(__name__)

# Register your models here.


@admin.register(models.Log)
class LogAdmin(admin.ModelAdmin):

    list_filter = ("nivel", "modulo")
    list_display = (
        "colored_msg",
        "nivel",
        "traceback",
        "create_datetime_format",
    )
    list_display_links = ("colored_msg",)
    list_per_page = 10

    def colored_msg(self, instance):
        if instance.nivel in [logging.NOTSET, logging.INFO]:
            color = "green"
        elif instance.nivel in [logging.WARNING, logging.DEBUG]:
            color = "orange"
        else:
            color = "red"
        return format_html(
            '<span style="color: {color};">{msg}</span>',
            color=color,
            msg=instance.mensaje,
        )

    colored_msg.short_description = "Mensaje"

    def traceback(self, instance):
        return format_html(
            "<pre><code>{content}</code></pre>",
            content=instance.trace if instance.trace else "",
        )

    def create_datetime_format(self, instance):
        return instance.timestamp.strftime("%Y-%m-%d %X")

    create_datetime_format.short_description = "Fecha creacion"
