from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from ... import models, wpa


class Command(BaseCommand):
    """configura la red wifi"""

    def handle(self, *args, **options):
        try:
            wpa.apply_wifi(models.Wifi.get_solo())
        except (OSError, ValidationError) as e:
            raise CommandError("No se pudo configurar el wifi: {}".format(e))
