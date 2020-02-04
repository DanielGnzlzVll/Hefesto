from django.core.management.base import BaseCommand

from ... import services


class Command(BaseCommand):
    """Realiza de forma repatida las consultas modbus."""

    def handle(self, *args, **options):
        services.procesar_consultas_loop()
