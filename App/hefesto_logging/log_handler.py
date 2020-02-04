import logging
import traceback


class DatabaseLogHandler(logging.Handler):
    """Log handler to internal database."""
    def emit(self, record):
        try:
            from .models import Log  # pylint: disable=import-outside-toplevel

            trace = None

            if record.exc_info:
                trace = traceback.format_exc()

            kwargs = {
                "modulo": record.name,
                "nivel": record.levelno,
                "mensaje": record.getMessage(),
                "trace": trace,
            }

            Log.objects.create(**kwargs)
        except:  # noqa
            pass
