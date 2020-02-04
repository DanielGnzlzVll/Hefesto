from django.core.management.base import BaseCommand

from ... import services


class Command(BaseCommand):
    """Envia datos a Azure IoTHub"""

    def handle(self, *args, **options):
        services.send_data()
