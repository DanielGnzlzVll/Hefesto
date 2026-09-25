from unittest import mock

import requests
from django.db import OperationalError
from django.test import SimpleTestCase

from . import services

BASE_URI = "https://hub.example/devices/dev1/messages/deviceBound/abc123"
HEADERS = {"Authorization": "token"}


def make_response(status_code=204, etag='"abc123"', body=None):
    response = mock.Mock(status_code=status_code, reason="reason")
    response.headers = {"etag": etag} if etag else {}
    response.content = b"{}"
    response.json.return_value = body or {"models": {}}
    return response


@mock.patch.object(services.requests, "post")
@mock.patch.object(services.requests, "delete")
@mock.patch.object(services.core_services, "process_message_from_server")
class HandleCloudMessageTests(SimpleTestCase):
    def handle(self, response):
        with self.assertLogs(services.logger, level="INFO") as logs:
            services.handle_cloud_message(
                response, "hub.example", "dev1", HEADERS
            )
        return logs

    def errors(self, logs):
        return [r for r in logs.records if r.levelname == "ERROR"]

    def test_successful_message_is_completed(self, process, delete, post):
        delete.return_value = make_response()

        logs = self.handle(make_response(body={"models": {"clean": []}}))

        process.assert_called_once_with({"models": {"clean": []}})
        delete.assert_called_once_with(
            f"{BASE_URI}?api-version=2018-04-01", headers=HEADERS, timeout=10
        )
        post.assert_not_called()
        self.assertEqual(self.errors(logs), [])
        self.assertIn("Mensaje completado: abc123", logs.output[-1])

    def test_failed_message_is_rejected_and_traceback_logged(
        self, process, delete, post
    ):
        process.side_effect = LookupError("unknown model")
        delete.return_value = make_response()

        logs = self.handle(make_response())

        delete.assert_called_once_with(
            f"{BASE_URI}?api-version=2018-04-01&reject",
            headers=HEADERS,
            timeout=10,
        )
        post.assert_not_called()
        errors = self.errors(logs)
        self.assertEqual(len(errors), 1)
        self.assertIs(errors[0].exc_info[0], LookupError)
        self.assertIn("Mensaje rechazado: abc123", logs.output[-1])

    def test_invalid_json_is_rejected(self, process, delete, post):
        delete.return_value = make_response()
        response = make_response()
        response.json.side_effect = ValueError("bad json")

        self.handle(response)

        process.assert_not_called()
        delete.assert_called_once_with(
            f"{BASE_URI}?api-version=2018-04-01&reject",
            headers=HEADERS,
            timeout=10,
        )

    def test_database_error_abandons_message(self, process, delete, post):
        process.side_effect = OperationalError("db down")
        post.return_value = make_response()

        logs = self.handle(make_response())

        post.assert_called_once_with(
            f"{BASE_URI}/abandon?api-version=2018-04-01",
            headers=HEADERS,
            timeout=10,
        )
        delete.assert_not_called()
        self.assertIs(self.errors(logs)[0].exc_info[0], OperationalError)
        self.assertIn("Mensaje abandonado: abc123", logs.output[-1])

    def test_failed_settle_response_is_logged(self, process, delete, post):
        delete.return_value = make_response(status_code=412)

        logs = self.handle(make_response())

        self.assertEqual(logs.records[-1].levelname, "ERROR")
        self.assertIn("412", logs.output[-1])
        self.assertIn("abc123", logs.output[-1])

    def test_settle_request_exception_is_logged(self, process, delete, post):
        delete.side_effect = requests.ConnectionError("unreachable")

        logs = self.handle(make_response())

        self.assertEqual(logs.records[-1].levelname, "ERROR")
        self.assertIs(logs.records[-1].exc_info[0], requests.ConnectionError)

    def test_response_without_etag_is_ignored(self, process, delete, post):
        services.handle_cloud_message(
            make_response(etag=""), "hub.example", "dev1", HEADERS
        )

        process.assert_not_called()
        delete.assert_not_called()
        post.assert_not_called()
