import datetime
import logging

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from ... import models

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Delete all logs older that 2 days."""

    def handle(self, *args, **options):
        try:
            time_limit = now() - datetime.timedelta(days=2)
            models.Log.objects.filter(timestamp__lt=time_limit).delete()
        except:  # noqa: E722 pylint: disable=bare-except
            pass
