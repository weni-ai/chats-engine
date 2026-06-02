from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from requests import HTTPError
from rest_framework.exceptions import APIException

from chats.apps.api.v1.internal.rest_clients.meta import MetaGraphAPIClient


META_BASE_URL = "https://graph.facebook.com"
FAKE_ACCESS_TOKEN = "fake-access-token"


@override_settings(
    META_GRAPH_API_BASE_HOST_URL=META_BASE_URL,
    WHATSAPP_API_ACCESS_TOKEN=FAKE_ACCESS_TOKEN,
)
class TestGetTemplatesList(TestCase):
    def setUp(self):
        self.client_rest = MetaGraphAPIClient()
        self.client_rest.base_host_url = META_BASE_URL
        self.client_rest.access_token = FAKE_ACCESS_TOKEN
        self.waba_id = "123456789"

    @patch("chats.apps.api.v1.internal.rest_clients.meta.requests.get")
    def test_get_templates_list_default_params(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        result = self.client_rest.get_templates_list(waba_id=self.waba_id)

        mock_get.assert_called_once_with(
            f"{META_BASE_URL}/v21.0/{self.waba_id}/message_templates",
            headers={"Authorization": f"Bearer {FAKE_ACCESS_TOKEN}"},
            params={"limit": 9999},
            timeout=60,
        )
        self.assertEqual(result, {"data": []})

    @patch("chats.apps.api.v1.internal.rest_clients.meta.requests.get")
    def test_get_templates_list_with_name_filter(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"name": "welcome"}]}
        mock_get.return_value = mock_response

        result = self.client_rest.get_templates_list(
            waba_id=self.waba_id, name="welcome"
        )

        called_params = mock_get.call_args.kwargs["params"]
        self.assertEqual(called_params["name"], "welcome")
        self.assertEqual(result, {"data": [{"name": "welcome"}]})

    @patch("chats.apps.api.v1.internal.rest_clients.meta.requests.get")
    def test_get_templates_list_with_fields(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        self.client_rest.get_templates_list(
            waba_id=self.waba_id, fields=["name", "status", "language"]
        )

        called_params = mock_get.call_args.kwargs["params"]
        self.assertEqual(called_params["fields"], "name,status,language")

    @patch("chats.apps.api.v1.internal.rest_clients.meta.requests.get")
    def test_get_templates_list_with_language_and_category(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        self.client_rest.get_templates_list(
            waba_id=self.waba_id, language="pt_BR", category="MARKETING"
        )

        called_params = mock_get.call_args.kwargs["params"]
        self.assertEqual(called_params["language"], "pt_BR")
        self.assertEqual(called_params["category"], "MARKETING")

    @patch("chats.apps.api.v1.internal.rest_clients.meta.requests.get")
    def test_get_templates_list_with_before_pagination(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [], "paging": {}}
        mock_get.return_value = mock_response

        self.client_rest.get_templates_list(
            waba_id=self.waba_id, before="cursor_abc"
        )

        called_params = mock_get.call_args.kwargs["params"]
        self.assertEqual(called_params["before"], "cursor_abc")
        self.assertNotIn("after", called_params)

    @patch("chats.apps.api.v1.internal.rest_clients.meta.requests.get")
    def test_get_templates_list_with_after_pagination(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [], "paging": {}}
        mock_get.return_value = mock_response

        self.client_rest.get_templates_list(
            waba_id=self.waba_id, after="cursor_xyz"
        )

        called_params = mock_get.call_args.kwargs["params"]
        self.assertEqual(called_params["after"], "cursor_xyz")
        self.assertNotIn("before", called_params)

    @patch("chats.apps.api.v1.internal.rest_clients.meta.requests.get")
    def test_get_templates_list_before_takes_precedence_over_after(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        self.client_rest.get_templates_list(
            waba_id=self.waba_id, before="cursor_abc", after="cursor_xyz"
        )

        called_params = mock_get.call_args.kwargs["params"]
        self.assertEqual(called_params["before"], "cursor_abc")
        self.assertNotIn("after", called_params)

    @patch("chats.apps.api.v1.internal.rest_clients.meta.requests.get")
    def test_get_templates_list_omits_none_optional_params(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        self.client_rest.get_templates_list(
            waba_id=self.waba_id,
            name=None,
            fields=None,
            language=None,
            category=None,
        )

        called_params = mock_get.call_args.kwargs["params"]
        self.assertNotIn("name", called_params)
        self.assertNotIn("fields", called_params)
        self.assertNotIn("language", called_params)
        self.assertNotIn("category", called_params)
        self.assertIn("limit", called_params)

    @patch("chats.apps.api.v1.internal.rest_clients.meta.requests.get")
    def test_get_templates_list_custom_limit(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        self.client_rest.get_templates_list(waba_id=self.waba_id, limit=50)

        called_params = mock_get.call_args.kwargs["params"]
        self.assertEqual(called_params["limit"], 50)

    @patch("chats.apps.api.v1.internal.rest_clients.meta.capture_exception")
    @patch("chats.apps.api.v1.internal.rest_clients.meta.requests.get")
    def test_get_templates_list_raises_api_exception_on_http_error(
        self, mock_get, mock_capture
    ):
        mock_capture.return_value = "evt-123"
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError(response=response)
        response.text = "Bad Request"
        mock_get.return_value = response

        with self.assertRaises(APIException) as ctx:
            self.client_rest.get_templates_list(waba_id=self.waba_id)

        mock_capture.assert_called_once()
        self.assertIn("evt-123", str(ctx.exception.detail))

    @patch("chats.apps.api.v1.internal.rest_clients.meta.capture_exception")
    @patch("chats.apps.api.v1.internal.rest_clients.meta.requests.get")
    def test_get_templates_list_http_error_has_meta_api_error_code(
        self, mock_get, mock_capture
    ):
        mock_capture.return_value = "evt-456"
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError(response=response)
        response.text = "Unauthorized"
        mock_get.return_value = response

        with self.assertRaises(APIException) as ctx:
            self.client_rest.get_templates_list(waba_id=self.waba_id)

        self.assertEqual(ctx.exception.status_code, 500)

    def test_headers_property(self):
        self.assertEqual(
            self.client_rest.headers,
            {"Authorization": f"Bearer {FAKE_ACCESS_TOKEN}"},
        )
