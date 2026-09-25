import functools
import logging

import django.apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import transaction

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
        return {}, lambda: None, process_message_from_server


FORBIDDEN_APPS = {
    "admin",
    "auth",
    "contenttypes",
    "sessions",
    "hefesto_logging",
    "hefesto_network",
    "hefesto_http_agent",
    "hefesto_azure_iothub",
}
FORBIDDEN_MODELS = {"hefesto_core.task"}
OPERATIONS = ("clean", "update")


class InvalidInstruction(Exception):
    pass


def process_message_from_server(msg):
    """
    Aplica las instrucciones enviadas por el servidor, solo sobre los
    modelos, operaciones y campos de settings.HEFESTO_SERVER_INSTRUCTIONS.
    Si alguna instruccion no es valida no se aplica ninguna.

    :raises InvalidInstruction: si el mensaje no es valido o no esta permitido
    """
    logger.info(f"Procesando mensaje: {msg}")
    if msg is None:
        return
    if not isinstance(msg, dict):
        raise InvalidInstruction("El mensaje debe ser un objeto")
    instructions = msg.get("models")
    if instructions is None:
        return
    actions = _parse_models(instructions)
    with transaction.atomic():
        for action in actions:
            action()


def _parse_models(instructions):
    if not isinstance(instructions, dict):
        raise InvalidInstruction("'models' debe ser un objeto")
    unknown = set(instructions) - set(OPERATIONS)
    if unknown:
        raise InvalidInstruction(
            f"Operaciones no permitidas: {sorted(unknown)}"
        )
    actions = []
    for item in _as_list(instructions, "clean"):
        actions.append(_queryset(item, "clean").delete)
    for item in _as_list(instructions, "update"):
        queryset = _queryset(item, "update")
        fields = _clean_fields(queryset.model, item.get("fields"))
        actions.append(functools.partial(queryset.update, **fields))
    return actions


def _as_list(instructions, operation):
    items = instructions.get(operation, [])
    if not isinstance(items, list) or not all(
        isinstance(item, dict) for item in items
    ):
        raise InvalidInstruction(
            f"'{operation}' debe ser una lista de objetos"
        )
    return items


def _get_model(name):
    try:
        return django.apps.apps.get_model(name)
    except (LookupError, ValueError, TypeError, AttributeError):
        raise InvalidInstruction(f"Modelo no valido: {name!r}")


def _allowed_operations(Model):
    label = Model._meta.label_lower
    if Model._meta.app_label in FORBIDDEN_APPS or label in FORBIDDEN_MODELS:
        return {}
    allowlist = getattr(settings, "HEFESTO_SERVER_INSTRUCTIONS", {})
    for name, operations in allowlist.items():
        if name.lower() == label:
            return operations
    return {}


def _local_field(Model, name):
    if name == "pk":
        return Model._meta.pk
    try:
        field = Model._meta.get_field(name)
    except FieldDoesNotExist:
        field = None
    if field is None or not field.concrete or field.is_relation:
        raise InvalidInstruction(
            f"Campo no valido en {Model._meta.label}: {name!r}"
        )
    return field


def _validate_lookups(Model, lookups):
    if not isinstance(lookups, dict):
        raise InvalidInstruction("'filter' y 'exclude' deben ser objetos")
    for key in lookups:
        name, _, lookup = key.partition("__")
        field = _local_field(Model, name)
        if lookup and field.get_lookup(lookup) is None:
            raise InvalidInstruction(
                f"Filtro no valido en {Model._meta.label}: {key!r}"
            )


def _queryset(item, operation):
    Model = _get_model(item.get("name"))
    if not _allowed_operations(Model).get(operation):
        raise InvalidInstruction(
            f"'{operation}' no permitido en {Model._meta.label}"
        )
    filter_ = item.get("filter", {})
    exclude_ = item.get("exclude", {})
    _validate_lookups(Model, filter_)
    _validate_lookups(Model, exclude_)
    try:
        return Model.objects.filter(**filter_).exclude(**exclude_)
    except (ValueError, TypeError, ValidationError) as e:
        raise InvalidInstruction(
            f"Filtro no valido en {Model._meta.label}: {e}"
        )


def _clean_fields(Model, fields):
    if not isinstance(fields, dict) or not fields:
        raise InvalidInstruction("'fields' debe ser un objeto no vacio")
    allowed = _allowed_operations(Model).get("update")
    cleaned = {}
    for name, value in fields.items():
        if name not in allowed:
            raise InvalidInstruction(
                f"Campo no permitido en {Model._meta.label}: {name!r}"
            )
        field = _local_field(Model, name)
        try:
            cleaned[field.attname] = field.clean(value, None)
        except ValidationError as e:
            raise InvalidInstruction(
                f"Valor no valido para {Model._meta.label}.{name}: "
                f"{e.messages}"
            )
    return cleaned
