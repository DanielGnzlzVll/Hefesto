from django.contrib import admin
from django.utils.timezone import now

# Register your models here.
from . import forms, models


class VariableLecturaInline(admin.TabularInline):
    model = models.VariableLectura
    extra = 0

    def get_extra(self, request, obj=None, **kwargs):
        if not obj:
            return 0
        return self.extra

    class Media:
        js = (
            r"admin/js/jquery.init.js",
            r"hefesto_modbus/js/hefesto_modbus_ascii.js",
        )


class VariableEscrituraInline(admin.TabularInline):
    model = models.VariableEscritura
    extra = 0

    def get_extra(self, request, obj=None, **kwargs):
        if not obj:
            return 0
        return self.extra


class ConsultaModelAdmin(admin.ModelAdmin):
    def habilitar_consulta(self, request, queryset):
        """
        habilita las consultas seleccionadas
        """
        for consulta in queryset.all():
            consulta.habilitada = True
            consulta.save()

    def deshabilitar_consulta(self, request, queryset):
        """
        deshabilita las consultas seleccionadas
        """
        for consulta in queryset.all():
            consulta.habilitada = False
            consulta.save()

    def realizar_consulta(self, request, queryset):
        """
        pone en cola inmediatamente las consultas seleccionadas
        """
        queryset.update(proximo_request=now())

    habilitar_consulta.short_description = (
        "Habilitar las consultas seleccionada/s"
    )
    deshabilitar_consulta.short_description = (
        "Deshabilitar las consultas seleccionada/s"
    )
    realizar_consulta.short_description = (
        "Realizar las consulta seleccionada/s"
    )
    save_as = True
    inlines = [VariableLecturaInline, VariableEscrituraInline]
    actions = [
        "realizar_consulta",
        "habilitar_consulta",
        "deshabilitar_consulta",
    ]
    list_display = [
        "nombre",
        "habilitada",
        "dispositivos",
        "intervalo_muestreo",
        "proximo_request",
        "registro_inicio",
        "numero_registros",
    ]
    list_filter = ["habilitada", "dispositivos", "intervalo_muestreo"]
    form = forms.ConsultaForm
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("nombre", "habilitada"),
                    ("tiempo_espera", "intervalo_muestreo"),
                    "tipo_conexion",
                )
            },
        ),
        (
            "CONEXION SERIAL",
            {
                "fields": (
                    ("puerto_serial", "baudrate"),
                    ("numero_bytes", "paridad", "bit_parada"),
                ),
                "classes": ["conexion_serial"],
            },
        ),
        (
            "CONEXION TCP",
            {"fields": (("puerto_tcp", "ip"),), "classes": ["conexion_tcp"]},
        ),
        (
            "DISPOSITIVOS",
            {
                "fields": (
                    ("dispositivos", "codigo_funcion"),
                    ("registro_inicio", "numero_registros"),
                )
            },
        ),
    )

    class Media:
        js = (
            r"admin/js/jquery.init.js",
            r"hefesto_modbus/js/hefesto_modbus.js",
        )


@admin.register(models.ModbusTimeSerie)
class ModbusTimeSerieAdmin(admin.ModelAdmin):
    list_display = [
        "time",
        "name",
        "value",
        "dev_id",
        "variable",
        "request_raw",
        "response_raw",
        "crc_ok",
    ]
    list_filter = ["name", "dev_id", "variable", "crc_ok"]


admin.site.register(models.Consulta, ConsultaModelAdmin)
