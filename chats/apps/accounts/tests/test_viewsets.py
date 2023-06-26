from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User


class UserDataTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.user = User.objects.get(pk=9)
        self.request_user = User.objects.get(pk=4)
        self.login_token = Token.objects.get_or_create(user=self.user)[0]

    def test_get_existent_user(self):
        url = reverse("user_data-detail")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url, data={"user_email": self.request_user.email})
        self.assertEqual(response.data.get("first_name"), self.request_user.first_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_non_existent_user(self):
        url = reverse("user_data-detail")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url, data={"user_email": "nonexistent@weni.ai"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_without_user(self):
        url = reverse("user_data-detail")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
