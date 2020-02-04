from django.forms import ModelForm, ChoiceField
from django.core.exceptions import ValidationError
from . import models
from .utils import ports


class ConsultaForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ConsultaForm, self).__init__(*args, **kwargs)
        self.fields["puerto_serial"] = ChoiceField(
            choices=ports(), required=False,
        )

    def clean_puerto_serial(self, *args, **kargs):
        tipo_conexion = self.cleaned_data["tipo_conexion"]
        puerto_serial = self.cleaned_data["puerto_serial"]
        if tipo_conexion == "RTU/SERIAL" and not puerto_serial:
            raise ValidationError(
                "Debe poner el puerto. tal vez no hay ninguno conectado?",
                code="puerto_serial",
            )
        if tipo_conexion == "RTU/SERIAL" and puerto_serial not in [x[0] for x in ports()]:
            raise ValidationError(
                "Parece que este puerto ya no esta conectado.",
                code="puerto_serial",
            )
        return self.cleaned_data["puerto_serial"]

    class Meta:
        model = models.Consulta
        fields = [
            "nombre",
            "habilitada",
            "dispositivos",
            "codigo_funcion",
            "registro_inicio",
            "numero_registros",
            "tiempo_espera",
            "intervalo_muestreo",
            "tipo_conexion",
            "puerto_serial",
            "baudrate",
            "numero_bytes",
            "paridad",
            "bit_parada",
            "puerto_tcp",
            "ip",
        ]
