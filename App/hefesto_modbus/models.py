import logging
import struct

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.timezone import now

from hefesto_core import models as hmodels

from .utils import parce_dev_list

logger = logging.getLogger(__name__)


# Create your models here.
class Consulta(models.Model):
    nombre = models.CharField(max_length=100)
    habilitada = models.BooleanField(blank=True, default=True)
    dispositivos = models.CharField(
        max_length=50, help_text="Lista dispositivos Ej: 1-3, 5, 7-9"
    )
    funcion_choices = [(x, x) for x in [3, 4, 6, 16]]
    codigo_funcion = models.PositiveIntegerField(
        choices=funcion_choices, default=3, blank=False, null=False
    )
    registro_inicio = models.PositiveIntegerField(
        default=0,
        blank=False,
        null=False,
        validators=[MaxValueValidator(65535)],
    )
    numero_registros = models.PositiveIntegerField(
        default=1,
        blank=False,
        null=False,
        help_text="" "Un registro son 2 BYTES Ej: un registro: 0xFFEE",
        validators=[MaxValueValidator(127)],
    )
    tiempo_espera = models.FloatField(
        default=1,
        blank=False,
        null=False,
        help_text=""
        "Numero de segundos para abortar la consulta sí no recibe respuesta.",
    )
    intervalo_muestreo = models.PositiveIntegerField(
        default=300, blank=False, null=False, help_text="Tiempo en segundos."
    )
    proximo_request = models.DateTimeField(
        editable=False, blank=True, null=True, default=now
    )
    CONEXIONES = (("RTU/SERIAL", ("RTU/SERIAL")), ("TCP/TCP", "TCP/TCP"))
    tipo_conexion = models.CharField(
        max_length=100, choices=CONEXIONES, default="RTU/SERIAL"
    )

    # ==========================================================================
    # CONEXION SERIAL
    # ==========================================================================
    puerto_serial = models.CharField(
        max_length=50,
        # default="/dev/ttyAMA0",
        # choices=ports(),
        blank=True,
        null=True,
        help_text="Si existe mas de un dispositivo"
        'USB, las direcciones "/dev/ttyUSBx" '
        "no seran persistentes entre reinicios",
    )
    baurates = (
        (9600, 9600),
        (19200, 19200),
        (38400, 38400),
        (56000, 56000),
        (57600, 57600),
        (76800, 76800),
        (115200, 115200),
    )

    baudrate = models.PositiveIntegerField(
        default=9600, choices=baurates, blank=True, null=True
    )
    bytes_list = (
        ("FIVEBITS", "FIVEBITS"),
        ("SIXBITS", "SIXBITS"),
        ("SEVENBITS", "SEVENBITS"),
        ("EIGHTBITS", "EIGHTBITS"),
    )
    numero_bytes = models.CharField(
        max_length=50,
        choices=bytes_list,
        default="EIGHTBITS",
        blank=True,
        null=True,
    )

    paridad_list = (
        ("PARITY_NONE", "PARITY_NONE"),
        ("PARITY_EVEN", "PARITY_EVEN"),
        ("PARITY_ODD", "PARITY_MARK"),
        ("PARITY_SPACE", "PARITY_SPACE"),
    )
    paridad = models.CharField(
        max_length=50,
        choices=paridad_list,
        default="PARITY_NONE",
        blank=True,
        null=True,
    )

    bits_ = (
        ("STOPBITS_ONE", "STOPBITS_ONE"),
        ("STOPBITS_ONE_POINT_FIVE", "STOPBITS_ONE_POINT_FIVE"),
        ("STOPBITS_TWO", "STOPBITS_TWO"),
    )
    bit_parada = models.CharField(
        max_length=50,
        choices=bits_,
        default="STOPBITS_ONE",
        blank=True,
        null=True,
    )
    # ==========================================================================
    # CONEXION TCP
    # ==========================================================================
    puerto_tcp = models.PositiveIntegerField(
        default=502, blank=True, null=True
    )
    ip = models.GenericIPAddressField(
        default="192.168.1.1", blank=True, null=True
    )

    def __str__(self):
        return self.nombre

    def save(self, *args, **kargs):
        if self.codigo_funcion in ([6, 16]):
            self.variablelectura_set.all().delete()
        if self.codigo_funcion in ([3, 4]):
            self.variableescritura_set.all().delete()
        super(Consulta, self).save(*args, **kargs)

    def clean(self):
        """ Mira si hay errores actuales."""
        errors = {}
        try:
            if max(parce_dev_list(self.dispositivos)) > 255:
                errors["dispositivos"] = "Valor maximo dispositivo 255"
        except:  # noqa
            errors["dispositivos"] = "Verifique los dispositivos"
        if len(errors) > 0:
            raise ValidationError(
                {
                    code: ValidationError(errors[code], code=code)
                    for code in errors
                }
            )


TIPOS_DATOS = (
    (">b", "int8"),
    (">h", "int16"),
    (">i", "int32"),
    (">q", "int64"),
    (">B", "uint8"),
    (">H", "uint16"),
    (">I", "uint32"),
    (">Q", "uint64"),
    (">f", "float32"),
    (">d", "float64"),
    ("s", "ascii"),
)
BYTE_ORDERS = (
    ("AB", "AB"),
    ("BA", "BA"),
    ("ABCD", "ABCD"),
    ("CDAB", "CDAB"),
    ("BADC", "BADC"),
    ("DCBA", "DCBA"),
    ("ABCDEFGH", "ABCDEFGH"),
    ("HGFEDCBA", "HGFEDCBA"),
)


class VariableLectura(models.Model):

    consulta = models.ForeignKey(Consulta, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=50, blank=False, null=False)
    tipo_dato = models.CharField(
        max_length=10,
        choices=TIPOS_DATOS,
        default="h",
        blank=False,
        null=False,
    )
    longitud_texto = models.IntegerField(default=1, null=True, blank=True)
    byte_order = models.CharField(
        max_length=8,
        choices=BYTE_ORDERS,
        default="AB",
        blank=False,
        null=False,
    )
    desplazamiento = models.IntegerField(
        default=0,
        blank=False,
        null=False,
        help_text="Numero de bytes para empezar a leer la respuesta.",
        validators=[MaxValueValidator(254)],
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        blank=False,
        null=False,
        help_text="Cantidad N para leer N*Tipo_dato,  crea Nombre1..NombreN",
    )
    escala = models.FloatField(
        default=1,
        blank=False,
        null=False,
        help_text=(
            "Factor para escalar la variable (1) primero escala"
            "Ej: (value*escala)+offset"
        ),
    )
    offset = models.FloatField(
        default=0,
        blank=False,
        null=False,
        help_text="Cantidad a sumar a la variable",
    )

    class Meta:
        unique_together = ("consulta", "nombre")

    def __str__(self):
        return self.nombre

    def save(self, *args, **kargs):
        if self.tipo_dato != "s":
            self.longitud_texto = 1

        if self.consulta.codigo_funcion in ([3, 4]):
            super(VariableLectura, self).save(*args, **kargs)

    def clean(self):
        if self.consulta.codigo_funcion in ([3, 4]):
            errors = {}
            len_tipo_dato = struct.calcsize(self.tipo_dato)
            len_tipo_dato *= self.longitud_texto
            len_byteorder = len(self.byte_order)
            
            if (
                len_byteorder != len_tipo_dato and len_tipo_dato > 1
            ) and self.tipo_dato != "s":
                errors["tipo_dato"] = "Tipo dato y byte order no compatibles"
            
            if self.tipo_dato != "s" and self.longitud_texto != 1:
                errors["longitud_texto"] = (
                    "No se permite una longitud de"
                    "texto diferente a '1' para este tipo de dato"
                )
            
            if (
                self.consulta.numero_registros * 2
                < len_tipo_dato * self.cantidad
            ):
                self.consulta.numero_registros = (
                    len_tipo_dato * self.cantidad
                ) / 2
                errors[
                    "cantidad"
                ] = "Cantidad no concuerda con el numero de registros a leer"
            
            if len(errors) > 0:
                raise ValidationError(
                    {
                        code: ValidationError(errors[code], code=code)
                        for code in errors
                    }
                )


class VariableEscritura(models.Model):
    consulta = models.ForeignKey(
        Consulta, on_delete=models.CASCADE, blank=True, null=True
    )
    nombre = models.CharField(max_length=100)
    expresion = models.TextField()
    tipo_dato = models.CharField(
        max_length=10,
        choices=TIPOS_DATOS,
        default="h",
        blank=False,
        null=False,
    )
    byte_order = models.CharField(
        max_length=8,
        choices=BYTE_ORDERS,
        default="AB",
        blank=False,
        null=False,
    )

    class Meta:
        unique_together = ("consulta", "nombre")

    def __str__(self):
        return self.nombre

    def save(self, *args, **kargs):
        if self.consulta.codigo_funcion in ([6, 16]):
            super(VariableEscritura, self).save(*args, **kargs)


class ModbusTimeSerie(hmodels.TimeSerie):

    dev_id = models.PositiveIntegerField()
    variable = models.ForeignKey(
        VariableLectura, on_delete=models.CASCADE, null=True, blank=True
    )
    request_raw = models.CharField(max_length=500)
    response_raw = models.CharField(max_length=500)
    crc_ok = models.BooleanField()
