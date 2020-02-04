import logging

from django.db.models import Subquery
from django.db.models.signals import post_save
from django.dispatch import receiver

from . import models

logger = logging.getLogger(__name__)


@receiver(post_save, dispatch_uid="on_save_timeserie")
def on_save_timeserie(sender, **kwargs):
    if issubclass(sender, models.TimeSerie):
        # ==========================================================================
        # Delete oldest timeseries
        # ==========================================================================
        try:
            newest = models.TimeSerie.objects.filter().order_by("-time")
            to_delete = models.TimeSerie.objects.exclude(
                id__in=Subquery(newest.values("id")[:10000])
            )
            to_delete.delete()
        except Exception as e:
            logger.error("Imposible limpiar datos viejos")
            logger.exception(e)
