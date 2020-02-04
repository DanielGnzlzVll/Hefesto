import logging

from django.core.management import call_command
from django.db.models.signals import post_save
from django.dispatch import receiver

from . import models

logger = logging.getLogger(__name__)


def config_wifi():
    try:
        call_command("config_wifi")
    except:  # noqa
        logger.error(
            "Algo inesperado ha ocurrido intentando configurar el wifi."
        )


@receiver(post_save, sender=models.Wifi)
def on_save_wifi(sender, instance, **kwargs):
    config_wifi()
