from django.apps import AppConfig


class HefestoCoreConfig(AppConfig):
    name = 'hefesto_core'

    def ready(self):
        from . import signals  # noqa
        # signals.scheduler.start()
