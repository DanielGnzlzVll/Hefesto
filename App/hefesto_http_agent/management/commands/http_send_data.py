from django.core.management.base import BaseCommand

from ... import services


class Command(BaseCommand):
    """Command inicial la transmision de datos hacia el servidor http"""

    def handle(self, *args, **options):
        services.send_data()
