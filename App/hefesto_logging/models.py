import logging

from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

LOG_LEVELS = (
    (logging.NOTSET, _("NotSet")),
    (logging.INFO, _("Info")),
    (logging.WARNING, _("Warning")),
    (logging.DEBUG, _("Debug")),
    (logging.ERROR, _("Error")),
    (logging.FATAL, _("Fatal")),
)


class Log(models.Model):
    """Log model to internal database."""

    timestamp = models.DateTimeField(default=now)
    modulo = models.CharField(max_length=200)
    nivel = models.PositiveSmallIntegerField(
        choices=LOG_LEVELS, default=logging.ERROR, db_index=True
    )
    mensaje = models.TextField()
    trace = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.mensaje

    class Meta:
        ordering = ("-timestamp",)
        verbose_name_plural = verbose_name = "Logging"
        indexes = [
            models.Index(fields=["timestamp", "nivel", "modulo"]),
        ]
