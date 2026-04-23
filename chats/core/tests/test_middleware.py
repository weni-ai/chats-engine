import json
from unittest.mock import patch

from django.test import TestCase, RequestFactory, override_settings

from chats.core.middleware import InternalErrorHandlerMiddleware


class InternalErrorHandlerMiddlewareTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = InternalErrorHandlerMiddleware(get_response=lambda r: None)

    @patch("chats.core.middleware.sentry_sdk.capture_exception")
    def test_returns_500_with_event_id(self, mock_capture):
        mock_capture.return_value = "abc123"
        request = self.factory.get("/")
        exception = ValueError("something went wrong")

        response = self.middleware.process_exception(request, exception)

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertEqual(data["code"], "INTERNAL_ERROR")
        self.assertEqual(data["message"], "An internal error has occurred")
        self.assertEqual(data["event_id"], "abc123")
        self.assertNotIn("detail", data)

    @override_settings(DEBUG=True)
    @patch("chats.core.middleware.sentry_sdk.capture_exception")
    def test_includes_detail_when_debug_is_true(self, mock_capture):
        mock_capture.return_value = "abc123"
        request = self.factory.get("/")
        exception = ValueError("something went wrong")

        response = self.middleware.process_exception(request, exception)

        data = json.loads(response.content)
        self.assertIn("detail", data)
        self.assertIsInstance(data["detail"], str)

    @patch("chats.core.middleware.sentry_sdk.capture_exception")
    def test_calls_sentry_capture_exception(self, mock_capture):
        mock_capture.return_value = "evt-id"
        request = self.factory.get("/")
        exception = RuntimeError("unexpected")

        self.middleware.process_exception(request, exception)

        mock_capture.assert_called_once_with(exception)

    @override_settings(DEBUG=False)
    @patch("chats.core.middleware.sentry_sdk.capture_exception")
    def test_does_not_include_detail_when_debug_is_false(self, mock_capture):
        mock_capture.return_value = "evt-id"
        request = self.factory.get("/")
        exception = Exception("fail")

        response = self.middleware.process_exception(request, exception)

        data = json.loads(response.content)
        self.assertNotIn("detail", data)

    @patch("chats.core.middleware.sentry_sdk.capture_exception")
    def test_response_content_type_is_json(self, mock_capture):
        mock_capture.return_value = "evt-id"
        request = self.factory.get("/")
        exception = Exception("fail")

        response = self.middleware.process_exception(request, exception)

        self.assertEqual(response["Content-Type"], "application/json")
