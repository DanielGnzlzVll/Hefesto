from django.db import models
from solo.models import SingletonModel
from django.core.validators import MinValueValidator


# Create your models here.
class Client(SingletonModel):
    connection_string = models.TextField()
    habilitado = models.BooleanField(
        default=True, help_text="Habilitar el agente de envio."
    )
    tiempo_entre_envios = models.IntegerField(
        default=15*60, help_text="Tiempo en segundos."
    )
    tiempo_entre_peticiones = models.IntegerField(
        default=30*60, help_text="Tiempo en segundos.",
        validators=[MinValueValidator(25*60)],
    )
    gzip_habilitado = models.BooleanField(
        default=False, help_text="Habilitar compresion."
    )

    class Meta:
        verbose_name = "AZURE IoTHub"
