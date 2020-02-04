import logging
import subprocess
import time
import os
import sys
import datetime
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
sys.path.append(os.getcwd())

import django  # noqa: E402
django.setup()
from django.conf import settings

from apscheduler.schedulers.background import BackgroundScheduler  # noqa: E402
from apscheduler.triggers.cron import CronTrigger  # noqa: E402

from hefesto_core import models  # noqa: E402

logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger(__name__)
logger.info("Iniciando ejecucion de tareas")
scheduler = BackgroundScheduler()


class function_wrap:
    def __init__(self, command, *args, **kargs):
        self.command = command
        self.__name__ = command

    def __call__(self, *args, **kargs):
        return subprocess.run(self.command, shell=True)


def main():
    sheduler = BackgroundScheduler()
    tasks = models.Task.objects.all()
    for task in tasks:
        sheduler.add_job(
            function_wrap(task.command),
            CronTrigger.from_crontab(task.cron_expression),
            id=str(task),
            next_run_time=datetime.datetime.now()
        )

    sheduler.start()
    while 1:
        time.sleep(1000)


if __name__ == "__main__":
    try:
        logger.info("Iniciando ejecucion de tareas")
        main()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        logger.error("La ejecucion de las tareas ha terminado")
        logger.exception(e)
        
