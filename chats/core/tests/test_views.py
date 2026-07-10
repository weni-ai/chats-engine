from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from chats.core.views import (
    get_auth_token,
    get_internal_headers,
    persist_keycloak_user_by_email,
    search_dict_list,
)


class SearchDictListTests(SimpleTestCase):
    def test_finds_match(self):
        data = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
        self.assertEqual(search_dict_list(data, "name", "b"), {"id": 2, "name": "b"})

    def test_returns_none(self):
        self.assertIsNone(search_dict_list([{"id": 1}], "id", 99))


@override_settings(
    OIDC_OP_TOKEN_ENDPOINT="https://auth.example/token",
    OIDC_ADMIN_CLIENT_ID="cid",
    OIDC_ADMIN_CLIENT_SECRET="secret",
    OIDC_OP_USERS_DATA_ENDPOINT="https://auth.example/users",
)
class KeycloakViewsTests(TestCase):
    @patch("chats.core.views.requests.post")
    def test_get_auth_token(self, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "tok123"}
        self.assertEqual(get_auth_token(), "Bearer tok123")
        mock_post.assert_called_once()

    @patch("chats.core.views.get_auth_token", return_value="Bearer tok")
    def test_get_internal_headers(self, _mock_token):
        headers = get_internal_headers()
        self.assertEqual(headers["Authorization"], "Bearer tok")
        self.assertIn("Content-Type", headers)

    @patch("chats.core.views.requests.get")
    @patch(
        "chats.core.views.get_internal_headers",
        return_value={"Authorization": "Bearer x"},
    )
    def test_persist_keycloak_user_success(self, _headers, mock_get):
        mock_get.return_value.json.return_value = [
            {
                "email": "kc@example.com",
                "firstName": "First",
                "lastName": "Last",
                "username": "kcuser",
            }
        ]
        mock_get.return_value.status_code = 200
        persist_keycloak_user_by_email("kc@example.com")
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.get(email="kc@example.com")
        self.assertEqual(user.first_name, "First")
        self.assertEqual(user.last_name, "Last")

    @patch("chats.core.views.requests.get")
    @patch(
        "chats.core.views.get_internal_headers",
        return_value={"Authorization": "Bearer x"},
    )
    def test_persist_keycloak_user_uses_username_fallback(self, _headers, mock_get):
        mock_get.return_value.json.return_value = [
            {"email": "kc2@example.com", "username": "onlyuser"}
        ]
        mock_get.return_value.status_code = 200
        persist_keycloak_user_by_email("kc2@example.com")
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.get(email="kc2@example.com")
        self.assertEqual(user.first_name, "onlyuser")

    @patch("chats.core.views.LOGGER")
    @patch("chats.core.views.requests.get")
    @patch(
        "chats.core.views.get_internal_headers",
        return_value={"Authorization": "Bearer x"},
    )
    def test_persist_keycloak_user_not_found(self, _headers, mock_get, mock_logger):
        mock_get.return_value.json.return_value = []
        mock_get.return_value.status_code = 404
        self.assertIsNone(persist_keycloak_user_by_email("missing@example.com"))
        mock_logger.debug.assert_called_once()
