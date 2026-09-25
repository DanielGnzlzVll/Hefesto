import errno
import os
import stat
import tempfile
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from . import models, wpa

EXISTING = """ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=CO
"""

MALICIOUS = [
    'x"\n}\nnetwork={\nssid="evil"\n',
    "a}b",
    'pass"word',
    "line\nbreak",
]


class ChangeSsidKeyTests(SimpleTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmpdir.name, "wpa_supplicant.conf")
        with open(self.path, "w") as f:
            f.write(EXISTING)
        os.chmod(self.path, 0o600)

    def tearDown(self):
        self.tmpdir.cleanup()

    def read(self):
        with open(self.path) as f:
            return f.read()

    def test_writes_hex_ssid_and_derived_psk(self):
        wpa.change_ssid_key("IEEE", "password", self.path)
        content = self.read()
        self.assertTrue(content.startswith(EXISTING))
        self.assertIn("ssid=49454545\n", content)
        self.assertIn(
            "psk=f42c6fc52df0ebef9ebb4b90b38a5f90"
            "2e83fe1b135a70e23aed762e9710a12e\n",
            content,
        )
        self.assertNotIn("password", content)

    def test_raw_hex_psk_is_written_as_is(self):
        raw = "AB" * 32
        wpa.change_ssid_key("net", raw, self.path)
        self.assertIn("psk={}\n".format(raw.lower()), self.read())

    def test_replaces_previous_hefesto_block(self):
        wpa.change_ssid_key("first", "password1", self.path)
        wpa.change_ssid_key("second", "password2", self.path)
        content = self.read()
        self.assertEqual(content.count("network={"), 1)
        self.assertIn("ssid={}\n".format(b"second".hex()), content)

    def test_special_characters_cannot_change_structure(self):
        for ssid in ['a"b}c', "{}#=\\'"]:
            for key in ['p"ss}word', "}\"'#={}\\"]:
                wpa.change_ssid_key(ssid, key, self.path)
                content = self.read()
                self.assertEqual(content.count("network={"), 1)
                self.assertEqual(content.count("}"), 1)
                self.assertNotIn('"', content.replace(EXISTING, ""))

    def test_newline_is_rejected_and_file_untouched(self):
        for ssid, key in [(MALICIOUS[0], "password"), ("net", MALICIOUS[3])]:
            with self.assertRaises(ValidationError):
                wpa.change_ssid_key(ssid, key, self.path)
        self.assertEqual(self.read(), EXISTING)

    def test_preserves_mode_and_leaves_no_temp_files(self):
        wpa.change_ssid_key("net", "password", self.path)
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        self.assertEqual(os.listdir(self.tmpdir.name), ["wpa_supplicant.conf"])

    def test_falls_back_to_in_place_write_on_ebusy(self):
        busy = OSError(errno.EBUSY, "Device or resource busy")
        with mock.patch("os.replace", side_effect=busy):
            wpa.change_ssid_key("net", "password", self.path)
        self.assertIn("ssid={}\n".format(b"net".hex()), self.read())
        self.assertEqual(os.listdir(self.tmpdir.name), ["wpa_supplicant.conf"])

    def test_missing_file_raises(self):
        os.unlink(self.path)
        with self.assertRaises(OSError):
            wpa.change_ssid_key("net", "password", self.path)


class ValidatorTests(SimpleTestCase):
    def test_valid_ssids(self):
        for ssid in ["a", "x" * 32, "ñandú", 'a"b}c']:
            wpa.validate_ssid(ssid)

    def test_invalid_ssids(self):
        for ssid in ["", "x" * 33, "ñ" * 17, "a\nb", "a\tb", "a\x7fb"]:
            with self.assertRaises(ValidationError, msg=repr(ssid)):
                wpa.validate_ssid(ssid)

    def test_valid_psks(self):
        for key in ["x" * 8, "x" * 63, "0123456789abcdef" * 4, 'p"ss}w0rd']:
            wpa.validate_psk(key)

    def test_invalid_psks(self):
        for key in ["x" * 7, "x" * 64, "g" * 64, "contraseña", "pass\nword"]:
            with self.assertRaises(ValidationError, msg=repr(key)):
                wpa.validate_psk(key)


class WifiCleanTests(SimpleTestCase):
    def test_blank_is_allowed(self):
        models.Wifi(wifi_ssid="", password="").clean()

    def test_invalid_values_produce_field_errors(self):
        with self.assertRaises(ValidationError) as ctx:
            models.Wifi(wifi_ssid="a\nb", password="short").clean()
        self.assertEqual(
            set(ctx.exception.message_dict), {"wifi_ssid", "password"}
        )

    def test_valid_values(self):
        models.Wifi(wifi_ssid="net", password="password").clean()
