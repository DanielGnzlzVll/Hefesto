import datetime
import logging
import subprocess
import time

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from ... import models

logger = logging.getLogger(__name__)


class function_wrap:
    def __init__(self, command, *args, **kargs):
        self.command = command
        self.__name__ = command

    def __call__(self, *args, **kargs):
        result = subprocess.run(
            self.command, shell=True, stderr=subprocess.PIPE, text=True
        )
        if result.returncode:
            logger.error(
                f"'{self.command}' termino con codigo {result.returncode}: "
                f"{result.stderr}"
            )
        else:
            logger.info(f"'{self.command}' termino con codigo 0")
        return result


class TaskReconciler:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.fingerprints = {}

    def reconcile(self, tasks):
        desired = {str(task.id): task for task in tasks}

        for job in self.scheduler.get_jobs():
            if job.id not in desired:
                job.remove()
                logger.info(f"la tarea '{job.name}' fue borrada")
        for job_id in set(self.fingerprints) - set(desired):
            del self.fingerprints[job_id]

        for job_id, task in desired.items():
            # Not `updated`: plugin AppConfig.ready() re-saves hidden tasks
            # on every manage.py run, which would reschedule them each pass.
            fingerprint = (task.name, task.command, task.cron_expression)
            if self.fingerprints.get(job_id) == fingerprint:
                continue
            self.fingerprints[job_id] = fingerprint
            self.schedule(job_id, task)

    def schedule(self, job_id, task):
        try:
            trigger = CronTrigger.from_crontab(
                task.cron_expression, timezone=pytz.UTC
            )
        except ValueError:
            logger.exception(f"la tarea '{task}' no pudo ser programada")
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            return
        self.scheduler.add_job(
            function_wrap(task.command),
            trigger,
            id=job_id,
            name=str(task),
            replace_existing=True,
            next_run_time=datetime.datetime.now(tz=pytz.UTC),
        )
        logger.info(f"la tarea '{task}' fue programada")


class Command(BaseCommand):
    """Corre todos procesos de los plugins."""

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=30,
            help="Segundos entre cada sincronizacion con la base de datos.",
        )

    def handle(self, *args, **options):
        scheduler = BackgroundScheduler(timezone=pytz.UTC)
        scheduler.start()
        reconciler = TaskReconciler(scheduler)
        while True:
            close_old_connections()
            try:
                reconciler.reconcile(models.Task.objects.filter(enable=True))
            except Exception:
                logger.exception("no se pudieron sincronizar las tareas")
            time.sleep(options["interval"])
