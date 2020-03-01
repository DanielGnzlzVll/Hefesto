import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class HefestoHttpAgentConfig(AppConfig):
    name = "hefesto_http_agent"

    def ready(self):
        from hefesto_core import models as hmodels
        try:
            t, _ = hmodels.Task.objects.get_or_create(name="http_send_data")
            t.command = "python manage.py http_send_data"
            t.cron_expression = "*/1 * * * *"
            t.hidden = True
            t.save()
        except:  # noqa
            pass
