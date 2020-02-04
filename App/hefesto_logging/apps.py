from django.apps import AppConfig


class HefestoLoggingConfig(AppConfig):
    name = 'hefesto_logging'

    def ready(self):
        from . import signals  # noqa
