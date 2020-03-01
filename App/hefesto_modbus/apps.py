from django.apps import AppConfig


class HefestoModbusConfig(AppConfig):
    name = 'hefesto_modbus'

    def ready(self):
        from hefesto_core import models as hmodels
        try:
            t, _ = hmodels.Task.objects.get_or_create(name="modbus_daemon")
            t.command = "python manage.py modbus_daemon"
            t.cron_expression = "*/1 * * * *"
            t.hidden = True
            t.save()
        except:  # noqa
            pass
