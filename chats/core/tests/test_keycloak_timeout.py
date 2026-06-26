from unittest.mock import MagicMock, patch

import requests
from django.conf import settings
from django.test import TestCase, override_settings

VIEWS_PATH = "chats.core.views"


def _build_response(status_code: int, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload or {}
    return response


@override_settings(
    OIDC_OP_TOKEN_ENDPOINT="https://keycloak.test/token",
    OIDC_ADMIN_CLIENT_ID="admin-client",
    OIDC_ADMIN_CLIENT_SECRET="admin-secret",
    OIDC_OP_USERS_DATA_ENDPOINT="https://keycloak.test/users",
    OIDC_TIMEOUT=5,
)
class GetAuthTokenTimeoutTests(TestCase):
    @patch(f"{VIEWS_PATH}.requests.post")
    def test_passes_timeout_to_post(self, mock_post):
        mock_post.return_value = _build_response(200, {"access_token": "tok123"})

        from chats.core.views import get_auth_token

        get_auth_token()

        call_kwargs = mock_post.call_args.kwargs
        self.assertEqual(call_kwargs["timeout"], 5)

    @patch(f"{VIEWS_PATH}.requests.post")
    def test_returns_bearer_token(self, mock_post):
        mock_post.return_value = _build_response(200, {"access_token": "tok123"})

        from chats.core.views import get_auth_token

        result = get_auth_token()

        self.assertEqual(result, "Bearer tok123")

    @patch(f"{VIEWS_PATH}.requests.post")
    def test_raises_timeout_exception_when_keycloak_is_slow(self, mock_post):
        mock_post.side_effect = requests.Timeout("keycloak timeout")

        from chats.core.views import get_auth_token

        with self.assertRaises(requests.Timeout):
            get_auth_token()


@override_settings(
    OIDC_OP_TOKEN_ENDPOINT="https://keycloak.test/token",
    OIDC_ADMIN_CLIENT_ID="admin-client",
    OIDC_ADMIN_CLIENT_SECRET="admin-secret",
    OIDC_OP_USERS_DATA_ENDPOINT="https://keycloak.test/users",
    OIDC_TIMEOUT=5,
)
class PersistKeycloakUserTimeoutTests(TestCase):
    @patch(f"{VIEWS_PATH}.requests.get")
    @patch(f"{VIEWS_PATH}.get_auth_token", return_value="Bearer tok123")
    def test_passes_timeout_to_get(self, _mock_auth, mock_get):
        mock_get.return_value = _build_response(
            200,
            [{"email": "user@test.com", "firstName": "Test", "lastName": "User"}],
        )

        from chats.core.views import persist_keycloak_user_by_email

        persist_keycloak_user_by_email("user@test.com")

        call_kwargs = mock_get.call_args.kwargs
        self.assertEqual(call_kwargs["timeout"], 5)

    @patch(f"{VIEWS_PATH}.requests.get")
    @patch(f"{VIEWS_PATH}.get_auth_token", return_value="Bearer tok123")
    def test_returns_early_when_user_not_found(self, _mock_auth, mock_get):
        mock_get.return_value = _build_response(404, [])

        from chats.core.views import persist_keycloak_user_by_email

        result = persist_keycloak_user_by_email("missing@test.com")

        self.assertIsNone(result)

    @patch(f"{VIEWS_PATH}.requests.get")
    @patch(f"{VIEWS_PATH}.get_auth_token", return_value="Bearer tok123")
    def test_raises_timeout_exception_when_keycloak_is_slow(
        self, _mock_auth, mock_get
    ):
        mock_get.side_effect = requests.Timeout("keycloak timeout")

        from chats.core.views import persist_keycloak_user_by_email

        with self.assertRaises(requests.Timeout):
            persist_keycloak_user_by_email("user@test.com")


class OidcTimeoutSettingTests(TestCase):
    def test_oidc_timeout_setting_exists(self):
        self.assertTrue(
            hasattr(settings, "OIDC_TIMEOUT"),
            "OIDC_TIMEOUT deve existir nas settings",
        )

    def test_oidc_timeout_default_is_five_seconds(self):
        with self.settings(OIDC_TIMEOUT=5):
            self.assertEqual(settings.OIDC_TIMEOUT, 5)

    def test_oidc_timeout_is_integer(self):
        self.assertIsInstance(settings.OIDC_TIMEOUT, int)
