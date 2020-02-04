from django.core.management.base import BaseCommand

from ... import services


class Command(BaseCommand):
    """Realiza una vez las consultas modbus."""

    def handle(self, *args, **options):
        services.procesar_consultas()
