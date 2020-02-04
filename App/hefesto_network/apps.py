from django.apps import AppConfig


class HefestoNetworkConfig(AppConfig):
    name = 'hefesto_network'

    def ready(self):
        from . import signals  # noqa
        # signals.config_wifi()
