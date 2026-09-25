import datetime
import struct
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils.timezone import now

from hefesto_core import models as hmodels

from . import models, services, utils


def rtu(frame):
    return frame + utils.crc16(frame).to_bytes(2, "big")


def tcp(frame):
    return b"\x00\x01\x00\x00" + len(frame).to_bytes(2, "big") + frame


def make_consulta(**kwargs):
    params = {
        "nombre": "med",
        "dispositivos": "1",
        "codigo_funcion": 3,
        "registro_inicio": 0,
        "numero_registros": 2,
    }
    params.update(kwargs)
    return models.Consulta.objects.create(**params)


class OrderDataTests(SimpleTestCase):
    def test_single_byte_is_unchanged(self):
        self.assertEqual(services.order_data(b"\x01", "AB"), b"\x01")

    def test_two_bytes(self):
        self.assertEqual(services.order_data(b"\x01\x02", "AB"), b"\x01\x02")
        self.assertEqual(services.order_data(b"\x01\x02", "BA"), b"\x02\x01")

    def test_four_bytes(self):
        data = b"\x01\x02\x03\x04"
        cases = {
            "ABCD": b"\x01\x02\x03\x04",
            "CDAB": b"\x03\x04\x01\x02",
            "BADC": b"\x02\x01\x04\x03",
            "DCBA": b"\x04\x03\x02\x01",
        }
        for byte_order, expected in cases.items():
            with self.subTest(byte_order=byte_order):
                self.assertEqual(
                    services.order_data(data, byte_order), expected
                )

    def test_eight_bytes(self):
        data = bytes(range(1, 9))
        self.assertEqual(services.order_data(data, "ABCDEFGH"), data)
        self.assertEqual(services.order_data(data, "HGFEDCBA"), data[::-1])


class ExtractDataTests(SimpleTestCase):
    def var(self, **kwargs):
        params = {
            "tipo_dato": ">h",
            "byte_order": "AB",
            "longitud_texto": 1,
            "desplazamiento": 0,
        }
        params.update(kwargs)
        return models.VariableLectura(**params)

    def test_int16(self):
        self.assertEqual(services.extract_data(b"\xff\xfe", self.var(), 1), -2)

    def test_uint16_byte_swapped(self):
        var = self.var(tipo_dato=">H", byte_order="BA")
        self.assertEqual(services.extract_data(b"\x34\x12", var, 1), 0x1234)

    def test_float32_word_swapped(self):
        raw = struct.pack(">f", 1.5)
        var = self.var(tipo_dato=">f", byte_order="CDAB")
        self.assertEqual(services.extract_data(raw[2:] + raw[:2], var, 1), 1.5)

    def test_offset_and_item_select_the_slice(self):
        data = b"\xaa\x00\x01\x00\x02\x00\x03"
        var = self.var(desplazamiento=1)
        self.assertEqual(services.extract_data(data, var, 1), 1)
        self.assertEqual(services.extract_data(data, var, 3), 3)

    def test_ascii(self):
        var = self.var(tipo_dato="s", longitud_texto=4)
        self.assertEqual(services.extract_data(b"ABCD", var, 1), b"ABCD")

    def test_short_data_raises_incorrect_size(self):
        with self.assertRaises(services.IncorrectSize):
            services.extract_data(b"\x01", self.var(), 1)


class CheckCrcTests(SimpleTestCase):
    def test_valid_crc(self):
        consulta = models.Consulta(tipo_conexion="RTU/SERIAL")
        response = rtu(b"\x01\x03\x02\x00\x01")
        self.assertTrue(services.check_crc(response, consulta))

    def test_invalid_crc(self):
        consulta = models.Consulta(id=7, tipo_conexion="RTU/SERIAL")
        response = b"\x01\x03\x02\x00\x01\x00\x00"
        with self.assertLogs(services.logger, "ERROR"):
            self.assertFalse(services.check_crc(response, consulta))

    def test_tcp_skips_crc(self):
        consulta = models.Consulta(tipo_conexion="TCP/TCP")
        self.assertTrue(services.check_crc(b"\x00", consulta))


class CheckNotErrorsTests(SimpleTestCase):
    read_request = rtu(b"\x01\x03\x00\x00\x00\x02")

    def consulta(self, **kwargs):
        params = {"codigo_funcion": 3, "numero_registros": 2}
        params.update(kwargs)
        return models.Consulta(**params)

    def assertRejected(self, request, response, consulta):
        with self.assertLogs(services.logger, "ERROR"):
            self.assertFalse(
                services.check_not_errors(request, response, consulta)
            )

    def test_rtu_read_ok(self):
        response = rtu(b"\x01\x03\x04\x00\x01\x00\x02")
        self.assertTrue(
            services.check_not_errors(
                self.read_request, response, self.consulta()
            )
        )

    def test_rtu_read_wrong_device(self):
        response = rtu(b"\x02\x03\x04\x00\x01\x00\x02")
        self.assertRejected(self.read_request, response, self.consulta())

    def test_rtu_read_byte_count_mismatch(self):
        response = rtu(b"\x01\x03\x02\x00\x01\x00\x02")
        self.assertRejected(self.read_request, response, self.consulta())

    def test_rtu_read_unexpected_length(self):
        response = rtu(b"\x01\x03\x02\x00\x01")
        self.assertRejected(self.read_request, response, self.consulta())

    def test_rtu_write_single(self):
        consulta = self.consulta(codigo_funcion=6, numero_registros=1)
        request = rtu(b"\x01\x06\x00\x01\x00\x0a")
        self.assertTrue(services.check_not_errors(request, request, consulta))
        self.assertRejected(request, rtu(b"\x01\x06\x00\x01\x00"), consulta)

    def test_rtu_write_multiple(self):
        consulta = self.consulta(codigo_funcion=16)
        request = rtu(b"\x01\x10\x00\x00\x00\x04\x00\x01\x00\x02")
        self.assertTrue(
            services.check_not_errors(
                request, rtu(b"\x01\x10\x00\x00\x00\x02"), consulta
            )
        )
        self.assertRejected(
            request, rtu(b"\x01\x10\x00\x00\x00\x01"), consulta
        )

    def test_tcp_read_ok(self):
        consulta = self.consulta(tipo_conexion="TCP/TCP")
        request = tcp(b"\x01\x03\x00\x00\x00\x02")
        response = tcp(b"\x01\x03\x04\x00\x01\x00\x02")
        self.assertTrue(services.check_not_errors(request, response, consulta))

    def test_tcp_transaction_mismatch(self):
        consulta = self.consulta(tipo_conexion="TCP/TCP")
        request = tcp(b"\x01\x03\x00\x00\x00\x02")
        response = b"\x00\x02" + tcp(b"\x01\x03\x04\x00\x01\x00\x02")[2:]
        self.assertRejected(request, response, consulta)

    def test_tcp_length_mismatch(self):
        request = tcp(b"\x01\x03\x00\x00\x00\x02")
        response = tcp(b"\x01\x03\x04\x00\x01\x00\x02") + b"\x00"
        self.assertFalse(
            services.check_not_errors_tcp(request, response, self.consulta())
        )


class FormarTramaTests(TestCase):
    def test_rtu_read(self):
        frame, response_length = services.formar_trama(make_consulta(), 1)
        self.assertEqual(frame, bytes.fromhex("010300000002c40b"))
        self.assertEqual(response_length, 4096)

    def test_tcp_read(self):
        consulta = make_consulta(tipo_conexion="TCP/TCP", registro_inicio=16)
        frame, _ = services.formar_trama(consulta, 5)
        self.assertEqual(frame, bytes.fromhex("000100000006050300100002"))

    def test_rtu_write_single(self):
        consulta = make_consulta(codigo_funcion=6, numero_registros=1)
        models.VariableEscritura.objects.create(
            consulta=consulta,
            nombre="setpoint",
            expresion="10",
            tipo_dato=">h",
        )
        frame, _ = services.formar_trama(consulta, 1)
        self.assertEqual(frame, rtu(b"\x01\x06\x00\x00\x00\x0a"))

    def test_write_multiple_truncates_values_to_register_count(self):
        consulta = make_consulta(codigo_funcion=16, numero_registros=1)
        for nombre, expresion in (("a", "1"), ("b", "2")):
            models.VariableEscritura.objects.create(
                consulta=consulta,
                nombre=nombre,
                expresion=expresion,
                tipo_dato=">h",
            )
        frame, _ = services.formar_trama(consulta, 1)
        self.assertEqual(frame[-4:-2], b"\x00\x01")
        self.assertTrue(services.check_crc(frame, consulta))


class EvaluarExpresionesTests(TestCase):
    def setUp(self):
        self.consulta = make_consulta(codigo_funcion=16)

    def add(self, nombre, expresion, tipo_dato=">h", **kwargs):
        models.VariableEscritura.objects.create(
            consulta=self.consulta,
            nombre=nombre,
            expresion=expresion,
            tipo_dato=tipo_dato,
            **kwargs,
        )

    def test_uses_latest_timeserie_value(self):
        hmodels.TimeSerie.objects.create(
            name="TEMP",
            value=1,
            plugin="test",
            time=now() - datetime.timedelta(minutes=1),
        )
        hmodels.TimeSerie.objects.create(name="TEMP", value=20, plugin="test")
        self.add("doble", "TEMP * 2")
        self.assertEqual(
            services.evaluar_expresiones(self.consulta, 1), b"\x00\x28"
        )

    def test_exposes_dev_math_and_timestamps(self):
        hmodels.TimeSerie.objects.create(name="TEMP", value=1, plugin="test")
        self.add("dev", "dev")
        self.add("math", "math.floor(2.7)")
        self.add("edad", "now - TEMP_time < 60")
        self.assertEqual(
            services.evaluar_expresiones(self.consulta, 3),
            b"\x00\x03\x00\x02\x00\x01",
        )

    def test_float_type_and_byte_order(self):
        self.add("valor", "1.5", tipo_dato=">f", byte_order="CDAB")
        raw = struct.pack(">f", 1.5)
        self.assertEqual(
            services.evaluar_expresiones(self.consulta, 1), raw[2:] + raw[:2]
        )

    def test_invalid_expression_is_skipped(self):
        self.add("malo", "UNDEFINED + 1")
        self.add("bueno", "7")
        self.assertEqual(
            services.evaluar_expresiones(self.consulta, 1), b"\x00\x07"
        )


class ObtenerConsultasTests(TestCase):
    def schedule(self, nombre, minutes, **kwargs):
        consulta = make_consulta(nombre=nombre, **kwargs)
        consulta.proximo_request = now() + datetime.timedelta(minutes=minutes)
        consulta.save()
        return consulta

    def test_returns_enabled_due_queries_oldest_first(self):
        later = self.schedule("later", -1)
        first = self.schedule("first", -5)
        self.schedule("disabled", -5, habilitada=False)
        self.schedule("future", 5)
        self.assertEqual(list(services.obtener_consultas()), [first, later])


class ProximoMuestreoTests(SimpleTestCase):
    def at(self, hour, minute, second=0, microsecond=0):
        return datetime.datetime(
            2026, 9, 25, hour, minute, second, microsecond,
            tzinfo=datetime.timezone.utc,
        )

    def test_aligns_to_next_interval_boundary(self):
        self.assertEqual(
            services.proximo_muestreo(300, self.at(10, 1, 13)),
            self.at(10, 5),
        )

    def test_boundary_moves_to_following_one(self):
        self.assertEqual(
            services.proximo_muestreo(300, self.at(10, 55)),
            self.at(11, 0),
        )

    def test_hour_boundary_is_sampled(self):
        self.assertEqual(
            services.proximo_muestreo(300, self.at(10, 58, 59, 999999)),
            self.at(11, 0),
        )

    def test_late_processing_skips_missed_boundaries(self):
        self.assertEqual(
            services.proximo_muestreo(60, self.at(10, 3, 30)),
            self.at(10, 4),
        )

    def test_hour_boundaries_align_to_local_time(self):
        lima = datetime.timezone(datetime.timedelta(hours=-5))
        desde = datetime.datetime(2026, 9, 25, 7, 40, tzinfo=lima)
        self.assertEqual(
            services.proximo_muestreo(3600, desde),
            datetime.datetime(2026, 9, 25, 8, 0, tzinfo=lima),
        )

    @override_settings(TIME_ZONE="Asia/Kolkata")
    def test_hour_boundaries_align_to_half_hour_offsets(self):
        self.assertEqual(
            services.proximo_muestreo(3600, self.at(10, 1)),
            self.at(10, 30),
        )

    def test_zero_interval_samples_immediately(self):
        desde = self.at(10, 1, 13)
        self.assertEqual(services.proximo_muestreo(0, desde), desde)


class ObtenerDriverTests(SimpleTestCase):
    def test_serial(self):
        consulta = models.Consulta(tipo_conexion="RTU/SERIAL")
        with mock.patch.object(services.drivers, "SerialDriver") as driver:
            result = services.obtener_driver(consulta)
        self.assertIs(result, driver.return_value)

    def test_tcp(self):
        consulta = models.Consulta(tipo_conexion="TCP/TCP")
        with mock.patch.object(services.drivers, "TPCDriver") as driver:
            result = services.obtener_driver(consulta)
        self.assertIs(result, driver.return_value)

    def test_unknown(self):
        consulta = models.Consulta(tipo_conexion="ASCII")
        with self.assertRaises(services.DriverNotFound):
            services.obtener_driver(consulta)


class ParseVariablesTests(TestCase):
    def add(self, consulta, nombre, **kwargs):
        models.VariableLectura.objects.create(
            consulta=consulta, nombre=nombre, **kwargs
        )

    def test_rtu_read_applies_scale_and_offset(self):
        consulta = make_consulta()
        self.add(consulta, "volt", tipo_dato=">h", escala=0.1, offset=1)
        request = rtu(b"\x01\x03\x00\x00\x00\x02")
        response = rtu(b"\x01\x03\x04\x00\x64\x00\x00")
        [item] = services.parse_variables(consulta, 1, request, response)
        self.assertEqual(item["name"], "MED__1__VOLT")
        self.assertAlmostEqual(item["value"], 11)
        self.assertEqual(item["dev_id"], 1)
        self.assertEqual(item["plugin"], "MODBUS RTU/SERIAL")
        self.assertEqual(item["request_raw"], request.hex(" "))
        self.assertEqual(item["response_raw"], response.hex(" "))
        self.assertEqual(
            item["context"],
            {"request": "med", "var_name": "volt", "device": 1},
        )

    def test_tcp_read_with_multiple_items(self):
        consulta = make_consulta(tipo_conexion="TCP/TCP")
        self.add(consulta, "i", tipo_dato=">H", cantidad=2)
        request = tcp(b"\x02\x03\x00\x00\x00\x02")
        response = tcp(b"\x02\x03\x04\x00\x05\x00\x06")
        items = services.parse_variables(consulta, 2, request, response)
        self.assertEqual(
            [(i["name"], i["value"]) for i in items],
            [("MED__2__I__1", 5.0), ("MED__2__I__2", 6.0)],
        )

    def test_ascii_strips_padding(self):
        consulta = make_consulta()
        self.add(consulta, "modelo", tipo_dato="s", longitud_texto=4)
        request = rtu(b"\x01\x03\x00\x00\x00\x02")
        response = rtu(b"\x01\x03\x04AB\x00\x00")
        [item] = services.parse_variables(consulta, 1, request, response)
        self.assertEqual(item["value"], "AB")

    def test_items_outside_response_are_skipped(self):
        consulta = make_consulta()
        self.add(consulta, "x", tipo_dato=">h", cantidad=3)
        request = rtu(b"\x01\x03\x00\x00\x00\x02")
        response = rtu(b"\x01\x03\x04\x00\x01\x00\x02")
        items = services.parse_variables(consulta, 1, request, response)
        self.assertEqual(
            [i["name"] for i in items], ["MED__1__X__1", "MED__1__X__2"]
        )

    def test_write_functions_return_no_variables(self):
        for codigo in (6, 16):
            with self.subTest(codigo=codigo):
                consulta = models.Consulta(codigo_funcion=codigo)
                self.assertEqual(
                    services.parse_variables(consulta, 1, b"", b""), []
                )


class GuardarVariablesTests(TestCase):
    def item(self, **kwargs):
        params = {
            "name": "MED__1__VOLT",
            "value": 12.5,
            "plugin": "MODBUS RTU/SERIAL",
            "dev_id": 1,
            "request_raw": "01",
            "response_raw": "02",
            "crc_ok": True,
        }
        params.update(kwargs)
        return params

    def test_creates_timeseries(self):
        services.guardar_variables([self.item(), self.item(name="OTHER")])
        names = models.ModbusTimeSerie.objects.values_list("name", flat=True)
        self.assertEqual(sorted(names), ["MED__1__VOLT", "OTHER"])

    def test_invalid_item_is_logged_and_skipped(self):
        with self.assertLogs(services.logger, "ERROR"):
            services.guardar_variables(
                [self.item(unknown_field=1), self.item()]
            )
        self.assertEqual(models.ModbusTimeSerie.objects.count(), 1)


class ProcesarConsultasTests(TestCase):
    def setUp(self):
        self.consulta = make_consulta(
            dispositivos="1-2", intervalo_muestreo=60
        )
        self.consulta.proximo_request = now() - datetime.timedelta(seconds=1)
        self.consulta.save()
        models.VariableLectura.objects.create(
            consulta=self.consulta, nombre="volt", tipo_dato=">h"
        )
        self.driver = mock.MagicMock()
        patcher = mock.patch.object(
            services, "obtener_driver", return_value=self.driver
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def respond(self, responses):
        self.driver.request.side_effect = lambda query, _: responses[query[0]]

    def test_saves_valid_responses_and_reschedules(self):
        self.respond(
            {
                1: rtu(b"\x01\x03\x04\x00\x0a\x00\x00"),
                2: rtu(b"\x02\x03\x04\x00\x14\x00\x00"),
            }
        )
        instante = now()
        with mock.patch.object(services, "now", return_value=instante):
            services.procesar_consultas()

        saved = models.ModbusTimeSerie.objects.values_list("name", "value")
        self.assertEqual(
            sorted(saved), [("MED__1__VOLT", 10.0), ("MED__2__VOLT", 20.0)]
        )
        self.driver.__enter__.assert_called_once()
        self.consulta.refresh_from_db()
        self.assertEqual(
            self.consulta.proximo_request,
            services.proximo_muestreo(60, instante),
        )

    def test_skips_missing_and_invalid_responses(self):
        bad_crc = b"\x02\x03\x04\x00\x14\x00\x00\x00\x00"
        self.respond({1: b"", 2: bad_crc})
        with self.assertLogs(services.logger, "INFO") as logs:
            services.procesar_consultas()
        self.assertEqual(models.ModbusTimeSerie.objects.count(), 0)
        self.assertTrue(any("sin respuesta" in m for m in logs.output))
        self.assertTrue(any("CRC" in m for m in logs.output))

    def test_driver_error_is_logged_without_rescheduling(self):
        scheduled = self.consulta.proximo_request
        self.driver.request.side_effect = OSError("timeout")
        with self.assertLogs(services.logger, "ERROR"):
            services.procesar_consultas()
        self.consulta.refresh_from_db()
        self.assertEqual(self.consulta.proximo_request, scheduled)
