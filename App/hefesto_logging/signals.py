import logging

from django.db.models import Subquery
from django.db.models.signals import post_save
from django.dispatch import receiver

from . import models

logger = logging.getLogger(__name__)


@receiver(post_save, sender=models.Log)
def on_save_log(sender, instance, created, **kwargs):
    # ==========================================================================
    # Delete oldest logs
    # ==========================================================================
    try:
        newest = models.Log.objects.filter().order_by("-timestamp")
        to_delete = models.Log.objects.exclude(
            id__in=Subquery(newest.values("id")[:5000])
        )
        to_delete.delete()
    except Exception as e:
        logger.error("Imposible limpiar logs viejos")
        logger.exception(e)
