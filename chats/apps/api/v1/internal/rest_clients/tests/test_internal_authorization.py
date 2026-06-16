from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase, override_settings

CLIENT_PATH = "chats.apps.api.v1.internal.rest_clients.internal_authorization"


def _build_response(status_code: int, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload or {}
    return response


@override_settings(
    OIDC_OP_TOKEN_ENDPOINT="https://keycloak.test/token",
    OIDC_RP_CLIENT_ID="rp-client",
    OIDC_RP_CLIENT_SECRET="rp-secret",
    OIDC_TIMEOUT=5,
)
class InternalAuthenticationTimeoutTests(TestCase):
    @patch(f"{CLIENT_PATH}.requests.post")
    def test_passes_timeout_to_post(self, mock_post):
        mock_post.return_value = _build_response(200, {"access_token": "tok123"})

        from chats.apps.api.v1.internal.rest_clients.internal_authorization import (
            InternalAuthentication,
        )

        auth = InternalAuthentication()
        auth.get_module_token()

        call_kwargs = mock_post.call_args.kwargs
        self.assertEqual(call_kwargs["timeout"], 5)

    @patch(f"{CLIENT_PATH}.requests.post")
    def test_returns_bearer_token(self, mock_post):
        mock_post.return_value = _build_response(200, {"access_token": "tok123"})

        from chats.apps.api.v1.internal.rest_clients.internal_authorization import (
            InternalAuthentication,
        )

        auth = InternalAuthentication()
        result = auth.get_module_token()

        self.assertEqual(result, "Bearer tok123")

    @patch(f"{CLIENT_PATH}.requests.post")
    def test_raises_timeout_exception_when_keycloak_is_slow(self, mock_post):
        mock_post.side_effect = requests.Timeout("keycloak timeout")

        from chats.apps.api.v1.internal.rest_clients.internal_authorization import (
            InternalAuthentication,
        )

        auth = InternalAuthentication()

        with self.assertRaises(requests.Timeout):
            auth.get_module_token()

    @patch(f"{CLIENT_PATH}.requests.post")
    def test_headers_property_includes_authorization(self, mock_post):
        mock_post.return_value = _build_response(200, {"access_token": "tok123"})

        from chats.apps.api.v1.internal.rest_clients.internal_authorization import (
            InternalAuthentication,
        )

        auth = InternalAuthentication()
        headers = auth.headers

        self.assertEqual(headers["Authorization"], "Bearer tok123")
        self.assertIn("Content-Type", headers)
