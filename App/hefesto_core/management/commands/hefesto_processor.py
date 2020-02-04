import logging
import subprocess
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand
from django.db.models.signals import post_save, post_delete

from ... import models

logger = logging.getLogger(__name__)


scheduler = BackgroundScheduler()


class function_wrap:
    def __init__(self, command, *args, **kargs):
        self.command = command
        self.__name__ = command

    def __call__(self, *args, **kargs):
        return subprocess.run(self.command, shell=True)


# @receiver(post_delete, sender=models.Task, dispatch_uid="on_delete_task")
def on_delete_task(sender, instance, **kwargs):
    try:
        scheduler.remove_job(str(instance))
        logger.info(f"la tarea '{instance}' fue borrada correctamente")
    except Exception as e:  # noqa
        logger.error(f"la tarea '{instance}' no pudo ser borrada")


# @receiver(post_save, sender=models.Task, dispatch_uid="on_save_task")
def on_save_task(sender, instance, created, **kwargs):
    if not created:
        try:
            scheduler.remove_job(str(instance))
            logger.info(f"la tarea '{instance}' fue borrada correctamente")
        except Exception as e:  # noqa
            logger.error(f"la tarea '{instance}' no pudo ser borrada")
            logger.exception(e)

    if instance.enable:
        try:
            scheduler.add_job(
                function_wrap(instance.command),
                CronTrigger.from_crontab(instance.cron_expression),
                id=str(instance),
            )
            logger.info(f"la tarea '{instance}' fue creada correctamente")
        except Exception as e:
            logger.error(f"la tarea '{instance}' no pudo ser creada")
            logger.exception(e)


class Command(BaseCommand):
    """Corre todos procesos de los plugins."""

    def handle(self, *args, **options):
        sheduler = BackgroundScheduler()
        tasks = models.Task.objects.all()
        for task in tasks:
            sheduler.add_job(
                function_wrap(task.command),
                CronTrigger.from_crontab(task.cron_expression),
                id=str(task),
            )
        post_delete.connect(
            on_delete_task, sender=models.Task, dispatch_uid="on_delete_task"
        )
        post_save.connect(
            on_save_task, sender=models.Task, dispatch_uid="on_save_task"
        )
        sheduler.start()
        while 1:
            time.sleep(1000)
