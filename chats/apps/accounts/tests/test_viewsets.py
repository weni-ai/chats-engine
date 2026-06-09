from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.accounts.tests.decorators import with_internal_auth


class UserDataTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.user = User.objects.get(pk=9)
        self.request_user = User.objects.get(pk=4)
        self.other_project_user = User.objects.get(pk=2)
        self.login_token = Token.objects.get_or_create(user=self.user)[0]

    def _auth_client(self):
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        return client

    def test_get_existent_user(self):
        url = reverse("user_data-detail")
        client = self._auth_client()
        response = client.get(url, data={"user_email": self.request_user.email})
        self.assertEqual(response.data.get("first_name"), self.request_user.first_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_non_existent_user(self):
        url = reverse("user_data-detail")
        client = self._auth_client()
        response = client.get(url, data={"user_email": "nonexistent@weni.ai"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_without_user_email_returns_400(self):
        url = reverse("user_data-detail")
        client = self._auth_client()
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("user_email", response.data)

    def test_get_user_in_different_project_returns_404(self):
        url = reverse("user_data-detail")
        client = self._auth_client()
        response = client.get(url, data={"user_email": self.other_project_user.email})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @with_internal_auth
    def test_get_user_in_different_project_internal_user_returns_200(self):
        url = reverse("user_data-detail")
        client = self._auth_client()
        response = client.get(url, data={"user_email": self.other_project_user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("first_name"), self.other_project_user.first_name
        )

    @with_internal_auth
    def test_get_existent_user_internal_user(self):
        url = reverse("user_data-detail")
        client = self._auth_client()
        response = client.get(url, data={"user_email": self.request_user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("first_name"), self.request_user.first_name)
