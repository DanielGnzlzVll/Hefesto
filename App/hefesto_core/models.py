from apscheduler.triggers.cron import CronTrigger
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now

from solo.models import SingletonModel


# Create your models here.
class DeviceConfiguration(SingletonModel):
    hefesto_id = models.CharField(
        max_length=100,
        blank=True,
        null=False,
        help_text=(
            "Identificador unico para usar en el envio de datos."
            "\nSi se deja en blanco, se usuara el serial de la CPU."
        ),
    )


class TimeSerie(models.Model):
    time = models.DateTimeField(default=now)
    name = models.CharField(max_length=50, blank=False, null=False)
    value = JSONField(default=dict)
    plugin = models.CharField(max_length=50, blank=False, null=False)
    context = JSONField(null=True, blank=True, default=dict)
    exported = models.NullBooleanField(null=True, default=False)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["time", "exported"]),
            models.Index(fields=["plugin", "name", "time"]),
        ]


def validate_cron(value):
    try:
        CronTrigger.from_crontab(value)
    except:  # noqa
        raise ValidationError(
            "'%(value)s' isn't a valid cron expresion", params={"value": value}
        )


class Task(models.Model):
    name = models.CharField(
        max_length=50, blank=False, null=False, unique=True
    )
    command = models.CharField(max_length=1024, blank=False, null=False)
    cron_expression = models.CharField(
        max_length=50, blank=False, null=False, validators=[validate_cron]
    )
    enable = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    hidden = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} [{self.id}]"
