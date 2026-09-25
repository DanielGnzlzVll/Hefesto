from unittest import mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from . import models, services


class ClientUrlTests(SimpleTestCase):
    def test_http_url_is_rejected(self):
        client = models.Client(url="http://example.com/data")
        with self.assertRaises(ValidationError) as ctx:
            client.clean_fields()
        self.assertIn("url", ctx.exception.message_dict)

    def test_https_url_is_accepted(self):
        models.Client(url="https://example.com/data").clean_fields()


class ProcessResponseTests(SimpleTestCase):
    def response(self, body=b'{"models": {}}'):
        response = mock.Mock(content=body)
        response.json.return_value = {"models": {}}
        return response

    def test_instructions_are_processed_over_https(self):
        processor = mock.Mock()
        config = models.Client(url="https://example.com")
        services.process_response(self.response(), config, processor)
        processor.assert_called_once_with({"models": {}})

    def test_instructions_are_ignored_over_http(self):
        processor = mock.Mock()
        config = models.Client(url="http://example.com")
        with self.assertLogs(services.logger, "WARNING"):
            services.process_response(self.response(), config, processor)
        processor.assert_not_called()

    def test_empty_body_is_ignored(self):
        processor = mock.Mock()
        config = models.Client(url="https://example.com")
        services.process_response(self.response(b""), config, processor)
        processor.assert_not_called()

    def test_processing_errors_are_logged(self):
        processor = mock.Mock(side_effect=ValueError("boom"))
        config = models.Client(url="https://example.com")
        with self.assertLogs(services.logger, "ERROR"):
            services.process_response(self.response(), config, processor)
