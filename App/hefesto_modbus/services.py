import datetime
import logging
import math
import struct
import time

from django.utils.timezone import now

from hefesto_core import models as hmodels

from . import drivers, models, utils

logger = logging.getLogger(__name__)


class DriverNotFound(Exception):
    pass


class IncorrectSize(Exception):
    pass


def obtener_consultas():
    return models.Consulta.objects.filter(
        habilitada=True, proximo_request__lt=now()
    ).order_by("proximo_request")


def obtener_driver(consulta):
    if consulta.tipo_conexion == "RTU/SERIAL":
        return drivers.SerialDriver(**consulta.__dict__)

    if consulta.tipo_conexion == "TCP/TCP":
        return drivers.TPCDriver(**consulta.__dict__)

    raise DriverNotFound(f"{consulta.tipo_conexion}")


def evaluar_expresiones(consulta, dev):
    _locals = {"now": now().timestamp(), "math": math, "dev": dev}
    timeseries = (
        hmodels.TimeSerie.objects.order_by("name", "-time")
        .distinct("name")
        .values()
    )
    _locals.update({var.get("name"): var.get("value") for var in timeseries})
    _locals.update(
        {
            var.get("name") + "_time": var.get("time").timestamp()
            for var in timeseries
        }
    )

    values = b""
    for variable in consulta.variableescritura_set.all():
        try:
            value = eval(variable.expresion, None, _locals)
            if variable.tipo_dato in ([">f", ">d"]):
                value = float(value)
            else:
                value = int(value)
            value_bytes = struct.pack(variable.tipo_dato, value)
            value_bytes = order_data(value_bytes, variable.byte_order)
            values += value_bytes
        except:  # noqa
            pass
    return values


def formar_trama(consulta, dev):

    frame = int(dev).to_bytes(1, "big")
    frame += (int(consulta.codigo_funcion)).to_bytes(1, "big")
    frame += (int(consulta.registro_inicio)).to_bytes(2, "big")

    if consulta.codigo_funcion in ([3, 4]):
        frame += (int(consulta.numero_registros)).to_bytes(2, "big")

    if consulta.codigo_funcion == 16:
        bytes_siguientes = int(consulta.numero_registros) * 2
        frame += (bytes_siguientes).to_bytes(2, "big")

    if consulta.codigo_funcion in ([6, 16]):
        values = evaluar_expresiones(consulta, dev)
        frame += values[: consulta.numero_registros * 2]

    if consulta.tipo_conexion == "RTU/SERIAL":
        frame += int(utils.crc16(frame)).to_bytes(2, "big")

    if consulta.tipo_conexion == "TCP/TCP":
        frame_tcp = int(1).to_bytes(2, "big")
        frame_tcp += int(0).to_bytes(2, "big")
        frame_tcp += int(len(frame)).to_bytes(2, "big")
        frame_tcp += frame
        frame = frame_tcp

    return frame, 4096


def check_crc(response, consulta):
    """
    CheckCRC comprueba si el crc de la trama esta bien

    :param frame_with_crc: trama recibida desde el equipo
    :type frame_with_crc: bytes
    :return: devuelve True si el crc esta bien, False en caso contrario
    :rtype: bool
    """

    if consulta.tipo_conexion == "TCP/TCP":
        return True
    try:
        frame_without = response[:-2]
        crc_recv = response[-2:]
        crc_teoric = utils.crc16(frame_without).to_bytes(2, "big")

        if crc_teoric == crc_recv:
            return True
        else:
            logger.error(
                f"CONSULTA CON ERROR DE CRC ID:{consulta.id}, "
                f"RECIBIDO: {crc_recv.hex(' ')}"
                f"ESPERADO: {crc_teoric.hex(' ')}"
            )
            return False
    except:  # noqa
        pass


def check_not_errors_rtu(requets_raw, response_raw, consulta):
    """
    Chequea si hay errores en la trama, formato RTU

    :param requets_raw: trama con la cual se hizo la solicitud
    :type requets_raw: bytes
    :param response_raw: trama de respuesta
    :type response_raw: bytes
    :return: True si la no hay errores
    :rtype: bool
    """

    OK = 1
    # codigo funcion y id no concuerdan con el requests
    if requets_raw[:2] != response_raw[:2]:
        logger.error(
            "Codigo de funcion y id del dispositivo no coincide con la consula"
        )
        OK = 0

    if consulta.codigo_funcion in ([3, 4]):
        # la longitud de datos no coincide con la que reporta el esclavo
        if len(response_raw) != (response_raw[2] + 3):
            logger.error(
                "La longitud de datos recibida no coincide con la reportada"
            )
            OK = 0

        # no es la longitud esperada
        if len(response_raw) != (3 + consulta.numero_registros * 2):
            logger.error(
                "La longitud de de la respuesta recibida no es la esperada"
            )
            OK = 0

    if consulta.codigo_funcion == 6:
        if len(response_raw) != 6:
            logger.error("El codigo de funcion en la respuesta no coincide")
            OK = 0

        # direccion del registro
        # TODO: 
        if response_raw[2:4] != response_raw[2:4]:
            OK = 0


    if consulta.codigo_funcion == 16:
        # direccion del registro
        # TODO:
        if response_raw[2:4] != response_raw[2:4]:
            OK = 0

        # int.from_bytes(response_raw[-2:], "big") numero de registros escritos
        if int.from_bytes(response_raw[-2:], "big") != (
            consulta.numero_registros
        ):
            logger.error("El numero de registros escritos no coincide")
            OK = 0

    return OK


def check_not_errors_tcp(requets_raw, response_raw, consulta):
    """
    Chequea si hay errores en la trama, formato TCP

    :param requets_raw: trama con la cual se hizo la solicitud
    :type requets_raw: bytes
    :param response_raw: trama de respuesta
    :type response_raw: bytes
    :return: True si la no hay errores
    :rtype: bool
    """

    OK = 1
    # codigo funcion y id no concuerdan con el requests
    if requets_raw[:5] != response_raw[:5]:
        OK = 0
    # la longitud de datos no coincide con la que reporta el esclavo que envia
    if len(response_raw[6:]) != (int.from_bytes(response_raw[4:6], "big")):
        OK = 0

    return OK


def check_not_errors(requets_raw, response_raw, consulta):
    """
    Chequea si hay errores en la trama

    :param requets_raw: trama con la cual se hizo la solicitud
    :type requets_raw: bytes
    :param response_raw: trama de respuesta
    :type response_raw: bytes
    :return: True si la no hay errores
    :rtype: bool
    """

    OK = 1
    if consulta.tipo_conexion == "RTU/SERIAL":
        OK = check_not_errors_rtu(
            requets_raw[:-2], response_raw[:-2], consulta
        )

    if consulta.tipo_conexion == "TCP/TCP":
        OK = min(
            check_not_errors_rtu(requets_raw[6:], response_raw[6:], consulta),
            check_not_errors_tcp(requets_raw, response_raw, consulta),
        )

    if not OK:
        logger.error(
            "CONSULTA CON ERRORES ID:{},  ENVIADO: {},  RECIBIDO:{}".format(
                consulta.id, requets_raw.hex(" "), response_raw.hex(" ")
            )
        )
    return OK


def order_data(data, byte_order):
    """
    Reordena los datos segun el byte_order de la variable/item
    """
    A_inx = byte_order.index("A") if "A" in byte_order else 0
    B_inx = byte_order.index("B") if "B" in byte_order else 0
    C_inx = byte_order.index("C") if "C" in byte_order else 0
    D_inx = byte_order.index("D") if "D" in byte_order else 0

    reordered = data
    if len(data) == 1:
        return reordered
    if len(data) == 2:
        if B_inx < A_inx:
            reordered = bytes([data[1], data[0]])
    if len(data) == 4:
        reordered = [1] * 4
        reordered[0] = data[A_inx]
        reordered[1] = data[B_inx]
        reordered[2] = data[C_inx]
        reordered[3] = data[D_inx]

        reordered = bytes(reordered)

    if len(data) == 8:

        if A_inx != 0:
            reordered = [1] * 8
            reordered[0] = data[7]
            reordered[1] = data[6]
            reordered[2] = data[5]
            reordered[3] = data[4]
            reordered[4] = data[3]
            reordered[5] = data[2]
            reordered[6] = data[1]
            reordered[7] = data[0]

            reordered = bytes(reordered)

    return reordered


def extract_data(data, var, item):
    size = struct.calcsize(var.tipo_dato) * var.longitud_texto
    tipo_dato = var.tipo_dato
    if var.tipo_dato == "s":
        tipo_dato = f"{int(size)}{tipo_dato}"
    data = data[(var.desplazamiento) + (item - 1) * size :]  # noqa: E203
    data = data[:size]
    data_reordered = (
        order_data(data, var.byte_order) if "s" not in tipo_dato else data
    )
    if size != len(data_reordered):
        raise IncorrectSize(f"{size} != {len(data_reordered)}")
    [value] = struct.unpack(tipo_dato, data_reordered)
    return value


def parse_variables_lectura(consulta, dev, request_raw, response_raw):

    package = ""
    if consulta.tipo_conexion == "RTU/SERIAL":
        package = response_raw[3:-2]
    if consulta.tipo_conexion == "TCP/TCP":
        package = response_raw[9:]
    var_list = []
    for var in consulta.variablelectura_set.all():
        item_dic = {
            "dev_id": dev,
            "variable_id": var.id,
            "response_raw": response_raw.hex(" "),
            "request_raw": request_raw.hex(" "),
            "crc_ok": True,
            "plugin": f"MODBUS {consulta.tipo_conexion}",
        }
        for item in range(1, var.cantidad + 1):
            item_dic["context"] = {
                "request": consulta.nombre,
                "var_name": var.nombre,
                "device": dev,
            }
            var_name = f"{consulta.nombre}__{dev}__{var.nombre}"
            if var.cantidad > 1:
                var_name += f"__{item}"
            item_dic["name"] = var_name.upper()

            try:
                value_raw = extract_data(package, var, item)
            except IncorrectSize:
                continue

            if var.tipo_dato == "s":
                item_dic["value"] = value_raw.decode().replace("\x00", "")
            else:
                item_dic["value"] = (
                    float(value_raw) * var.escala
                ) + var.offset

            var_list.append(item_dic.copy())
    return var_list


def parse_variables_escritura(consulta, dev, request_raw, response_raw):
    return []


def parse_variables(consulta, dev, request_raw, response_raw):
    if consulta.codigo_funcion in ([3, 4]):
        return parse_variables_lectura(
            consulta, dev, request_raw, response_raw
        )
    if consulta.codigo_funcion in ([6, 16]):
        return parse_variables_escritura(
            consulta, dev, request_raw, response_raw
        )

    return []


def guardar_variables(var_list):

    for item in var_list:
        try:
            logger.debug(f"Guardando ModbusTimeserie: {item}")
            models.ModbusTimeSerie.objects.create(**item)
        except Exception as e:
            logger.error("Imposible crear modbus timeseries")
            logger.exception(e)


def procesar_consultas():
    for consulta in obtener_consultas():
        try:
            driver = obtener_driver(consulta)
            with driver:
                for dev in utils.parce_dev_list(consulta.dispositivos):
                    query_raw, response_lenght = formar_trama(consulta, dev)
                    response_raw = driver.request(query_raw, response_lenght)
                    if (
                        query_raw is None
                        or response_raw == b""
                        or len(response_raw) <= 1
                    ):
                        logger.info(
                            f"Consulta sin respuesta: {query_raw.hex(' ')}"
                        )
                        continue
                    if not (
                        check_not_errors(query_raw, response_raw, consulta)
                        and check_crc(response_raw, consulta)
                    ):
                        continue
                    variables = parse_variables(
                        consulta, dev, query_raw, response_raw
                    )
                    guardar_variables(variables)
            consulta.proximo_request = now() + datetime.timedelta(
                seconds=consulta.intervalo_muestreo
            )
            consulta.save()
        except Exception as e:
            logger.error(f"Error en la consulta: {consulta.nombre}")
            logger.exception(e)


def procesar_consultas_loop():
    while 1:
        try:
            procesar_consultas()
        except (SystemExit, KeyboardInterrupt):
            break
        except Exception as e:
            logger.error("Error procesando consultas")
            logger.exception(e)
            time.sleep(60)
        # mejora el rendimiento en terminos de uso de la CPU
        # de 86% a 7% en las pruebas.
        time.sleep(0.1)
