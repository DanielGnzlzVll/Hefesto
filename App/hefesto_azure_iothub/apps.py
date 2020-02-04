from django.apps import AppConfig


class HefestoAzureIothubConfig(AppConfig):
    name = "hefesto_azure_iothub"

    def ready(self):
        from hefesto_core import models as hmodels

        try:
            t, _ = hmodels.Task.objects.get_or_create(
                name="azure_iothub_send_data"
            )
            t.command = "python manage.py azure_send_data"
            t.cron_expression = "*/5 * * * *"
            t.hidden = True
            t.save()
        except:  # noqa
            pass
        try:
            t, _ = hmodels.Task.objects.get_or_create(
                name="azure_iothub_get_data"
            )
            t.command = "python manage.py azure_get_data"
            t.cron_expression = "*/5 * * * *"
            t.hidden = True
            t.save()
        except:  # noqa
            pass
