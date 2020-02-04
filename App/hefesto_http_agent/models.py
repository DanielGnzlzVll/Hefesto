from django.db import models
from solo.models import SingletonModel


# Create your models here.
class Client(SingletonModel):
    url = models.URLField(
        max_length=200, default="http://localhost/hefesto/hefesto_web/data"
    )
    username = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nombre de usuario para 'Basic Auth'.",
    )
    password = models.CharField(
        max_length=100, blank=True, help_text="Contraseña para 'Basic Auth'."
    )
    habilitado = models.BooleanField(
        default=False, help_text="Habilitar el agente de envio."
    )
    gzip_habilitado = models.BooleanField(
        default=True, help_text="Habilitar compresion."
    )
    tiempo_entre_envios = models.IntegerField(
        default=60, help_text="Tiempo en segundos."
    )

    class Meta:
        verbose_name = "HTTP CLIENT"


class Header(models.Model):
    config = models.ForeignKey(Client, on_delete=models.CASCADE)
    key = models.TextField(blank=False, null=False)
    value = models.TextField(blank=False, null=False)
