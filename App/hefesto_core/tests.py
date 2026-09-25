from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from hefesto_core import core_services, models
from hefesto_http_agent import models as http_models
from hefesto_modbus.models import Consulta
from hefesto_network.models import Wifi

ALLOW_ALL_CONSULTA = {
    "hefesto_modbus.Consulta": {
        "clean": True,
        "update": ["habilitada", "intervalo_muestreo"],
    },
}


def update(name, fields, filter_=None):
    item = {"name": name, "fields": fields}
    if filter_ is not None:
        item["filter"] = filter_
    return {"models": {"update": [item]}}


@override_settings(HEFESTO_SERVER_INSTRUCTIONS=ALLOW_ALL_CONSULTA)
class ProcessMessageFromServerTests(TestCase):
    def setUp(self):
        self.consulta = Consulta.objects.create(
            nombre="test", dispositivos="1", intervalo_muestreo=300
        )
        self.otra = Consulta.objects.create(
            nombre="otra", dispositivos="2", intervalo_muestreo=300
        )

    def process(self, msg):
        core_services.process_message_from_server(msg)

    def assert_rejected(self, msg):
        with self.assertRaises(core_services.InvalidInstruction):
            self.process(msg)

    def test_allowed_update_is_applied(self):
        self.process(
            update(
                "hefesto_modbus.Consulta",
                {"intervalo_muestreo": 60, "habilitada": False},
                {"nombre": "test"},
            )
        )
        self.consulta.refresh_from_db()
        self.otra.refresh_from_db()
        self.assertEqual(self.consulta.intervalo_muestreo, 60)
        self.assertFalse(self.consulta.habilitada)
        self.assertEqual(self.otra.intervalo_muestreo, 300)

    def test_model_label_is_case_insensitive(self):
        self.process(
            update("hefesto_modbus.consulta", {"intervalo_muestreo": 60})
        )
        self.consulta.refresh_from_db()
        self.assertEqual(self.consulta.intervalo_muestreo, 60)

    def test_allowed_clean_with_filter_and_exclude(self):
        self.process(
            {
                "models": {
                    "clean": [
                        {
                            "name": "hefesto_modbus.Consulta",
                            "filter": {"nombre__in": ["test", "otra"]},
                            "exclude": {"nombre": "otra"},
                        }
                    ]
                }
            }
        )
        self.assertEqual(
            list(Consulta.objects.values_list("nombre", flat=True)), ["otra"]
        )

    def test_field_outside_allowlist_is_rejected(self):
        self.assert_rejected(
            update("hefesto_modbus.Consulta", {"puerto_serial": "/dev/x"})
        )

    def test_invalid_value_is_rejected(self):
        self.assert_rejected(
            update("hefesto_modbus.Consulta", {"intervalo_muestreo": -1})
        )

    def test_nothing_is_written_when_any_instruction_is_rejected(self):
        msg = {
            "models": {
                "clean": [{"name": "hefesto_modbus.Consulta"}],
                "update": [
                    {
                        "name": "hefesto_modbus.Consulta",
                        "fields": {"intervalo_muestreo": 60},
                    },
                    {
                        "name": "hefesto_core.Task",
                        "fields": {"command": "id"},
                    },
                ],
            }
        }
        self.assert_rejected(msg)
        self.assertEqual(Consulta.objects.count(), 2)
        self.consulta.refresh_from_db()
        self.assertEqual(self.consulta.intervalo_muestreo, 300)

    @override_settings(HEFESTO_SERVER_INSTRUCTIONS={})
    def test_clean_outside_allowlist_is_rejected(self):
        self.assert_rejected(
            {"models": {"clean": [{"name": "hefesto_modbus.Consulta"}]}}
        )
        self.assertEqual(Consulta.objects.count(), 2)

    @override_settings(
        HEFESTO_SERVER_INSTRUCTIONS={
            "hefesto_core.Task": {"clean": True, "update": ["command"]},
            "auth.User": {"clean": True, "update": ["is_superuser"]},
            "hefesto_network.Wifi": {"clean": True, "update": ["wifi_ssid"]},
            "hefesto_http_agent.Client": {"clean": True, "update": ["url"]},
        }
    )
    def test_protected_models_cannot_be_changed_even_if_allowlisted(self):
        task = models.Task.objects.create(
            name="t", command="echo ok", cron_expression="* * * * *"
        )
        user = User.objects.create(username="operator", id=1000)
        wifi = Wifi.objects.create(wifi_ssid="home", password="password")
        client = http_models.Client.get_solo()
        cases = [
            ("hefesto_core.Task", {"command": "id"}),
            ("auth.User", {"is_superuser": True}),
            ("hefesto_network.Wifi", {"wifi_ssid": "evil"}),
            ("hefesto_http_agent.Client", {"url": "https://evil"}),
        ]
        for name, fields in cases:
            with self.subTest(name=name):
                self.assert_rejected(update(name, fields))
                self.assert_rejected({"models": {"clean": [{"name": name}]}})
        task.refresh_from_db()
        user.refresh_from_db()
        wifi.refresh_from_db()
        client.refresh_from_db()
        self.assertEqual(task.command, "echo ok")
        self.assertFalse(user.is_superuser)
        self.assertEqual(wifi.wifi_ssid, "home")
        self.assertEqual(client.url, http_models.Client().url)

    def test_fixtures_are_rejected(self):
        users = User.objects.count()
        self.assert_rejected(
            {
                "models": {
                    "fixtures": [
                        {
                            "model": "auth.user",
                            "pk": 99,
                            "fields": {"username": "x", "is_superuser": True},
                        }
                    ]
                }
            }
        )
        self.assertEqual(User.objects.count(), users)

    def test_related_lookups_are_rejected(self):
        for key in ["variablelectura__nombre", "nombre__foo", "nope"]:
            with self.subTest(key=key):
                self.assert_rejected(
                    update(
                        "hefesto_modbus.Consulta",
                        {"intervalo_muestreo": 60},
                        {key: "x"},
                    )
                )

    def test_malformed_payloads_are_rejected(self):
        payloads = [
            "models",
            ["models"],
            {"models": []},
            {"models": {"update": {}}},
            {"models": {"update": ["x"]}},
            {"models": {"update": [{"fields": {"habilitada": False}}]}},
            {"models": {"update": [{"name": "nope"}]}},
            {"models": {"update": [{"name": "nope.Nope"}]}},
            {"models": {"update": [{"name": 3}]}},
            update("hefesto_modbus.Consulta", {}),
            update("hefesto_modbus.Consulta", ["habilitada"]),
            update(
                "hefesto_modbus.Consulta",
                {"habilitada": False},
                {"intervalo_muestreo": "abc"},
            ),
            {
                "models": {
                    "update": [
                        {
                            "name": "hefesto_modbus.Consulta",
                            "filter": [],
                            "fields": {"habilitada": False},
                        }
                    ]
                }
            },
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                self.assert_rejected(payload)
        self.assertEqual(
            Consulta.objects.filter(habilitada=True).count(), 2
        )

    def test_empty_messages_are_ignored(self):
        for msg in [None, {}, {"models": None}, {"models": {}}]:
            with self.subTest(msg=msg):
                self.process(msg)


class GetData2SendTests(TestCase):
    def test_processor_is_returned_without_pending_data(self):
        data, _, processor = core_services.get_data2send()
        self.assertEqual(data, {})
        self.assertIs(processor, core_services.process_message_from_server)
