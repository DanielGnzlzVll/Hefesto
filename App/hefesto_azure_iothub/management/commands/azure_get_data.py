from django.core.management.base import BaseCommand

from ... import services


class Command(BaseCommand):
    """Obtiene datos desde Azure IoTHub"""

    def handle(self, *args, **options):
        services.get_data()
