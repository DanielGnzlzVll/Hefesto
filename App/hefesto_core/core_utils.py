import logging
import threading
import time

from django.conf import settings

logger = logging.getLogger(__name__)


def get_serial():
    try:
        from hefesto_core import models
        config = models.DeviceConfiguration.get_solo()
        if config.hefesto_id is None or len(config.hefesto_id) == 0:
            return settings.HEFESTO_SERIAL
        return config.hefesto_id
    except:
        pass
    return settings.HEFESTO_SERIAL


def run_as_thread(function, time_between_calls=60, sleep_on_error=60):
    time.sleep(30)

    def wrap():
        logger.info(f"Iniciando ejecucion de: '{function.__name__}'")
        while 1:
            try:
                function()
            except KeyboardInterrupt:
                return
            except Exception as e:
                logger.error(f"Error ejecutando: '{function.__name__}'")
                logger.exception(e)
                time.sleep(sleep_on_error)

    thread = threading.Thread(target=wrap)
    thread.daemon = True
    thread.start()
    return thread
