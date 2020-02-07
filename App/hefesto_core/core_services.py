import logging
from django.db import transaction
import django.apps
import subprocess
import json
from hefesto_core import models

logger = logging.getLogger(__name__)


def _set_timeseries_as_update_callback(data_queryset):
    return lambda: models.TimeSerie.objects.filter(
        id__in=data_queryset
    ).update(exported=1)


def get_data2send():
    """
    Obtiene los timeseries desde la base de datos
    y las devuelve, siempre que no hayan sido enviadas al servidor,
    ademas devuelve una funcion callbakc que debe ser llamada cuando
    los datos hayan sido enviados correctamente, y otro para procesar
    la respuesta.

    ex:
    ===========
    data, success, processor = get_data2send()
    response = send(data)
    if len(response.body):
        processor(response.body)
    if response.ok:
        success()

    :return: diccionario con los datos de las variables
    :rtype: dict
    :return: funcion callback para el envio exito de datos.
    :rtype: func
    :return: funcion encargada de procesar la respuesta.
    :rtype: func
    """

    data_queryset = models.TimeSerie.objects.filter(exported=False).order_by(
        "-time"
    )[:1000]
    success_callback = _set_timeseries_as_update_callback(data_queryset)
    timeseries_list = []
    for timeserie in data_queryset:
        timeserie_json = {}
        timeserie_json["timestamp"] = str(timeserie.time)
        timeserie_json["var-name"] = timeserie.name
        timeserie_json["value"] = timeserie.value
        timeserie_json["plugin"] = timeserie.plugin
        timeserie_json["context"] = timeserie.context
        timeseries_list.append(timeserie_json)
    if len(timeseries_list) > 0:
        timeseries_list.reverse()
        return (
            {"TIMESERIES": timeseries_list},
            success_callback,
            process_message_from_server,
        )
    else:
        return {}, lambda: None, lambda: None


def process_message_from_server(msg):
    logger.info(f"Procesando mensaje: {msg}")
    with transaction.atomic():
        process_models(msg.get("models"))


def process_models(instructions):
    clean_models = instructions.get("clean", [])
    for model in clean_models:
        model_name = model.get("name")
        filter_ = model.get("filter", {})
        exclude_ = model.get("exclude", {})
        Model = django.apps.apps.get_model(model_name)
        Model.objects.filter(**filter_).exclude(**exclude_).delete()
    update_models = instructions.get("update", [])
    for model in update_models:
        model_name = model.get("name")
        filter_ = model.get("filter", {})
        exclude_ = model.get("exclude", {})
        to_update = model.get("fields")
        Model = django.apps.apps.get_model(model_name)
        Model.objects.filter(**filter_).exclude(**exclude_).update(**to_update)
    fixture_models = instructions.get("fixtures", None)
    if fixture_models:
        fixture_models = json.dumps(fixture_models).encode()
        cmd = ["python", "manage.py", "loaddata", "--format", "json", "-"]
        subprocess.run(cmd, input=fixture_models)
