import datetime
import logging

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from ... import models

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Borrar todos los datos de timeseries que tengan mas de 30 dias"""

    def handle(self, *args, **options):
        try:
            time_limit = now() - datetime.timedelta(days=30)
            models.TimeSerie.objects.filter(created__lt=time_limit).delete()
        except:  # noqa: 
            pass
