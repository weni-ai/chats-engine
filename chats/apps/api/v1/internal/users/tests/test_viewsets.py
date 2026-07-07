from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from chats.apps.accounts.models import User
from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.api.utils import create_user_and_token


class TestInternalUserViewSetCreate(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, token = create_user_and_token("internal-user")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

    def _create_url(self):
        return reverse("user_internal-list")

    def test_create_without_permission_returns_validation_error(self):
        response = self.client.post(
            self._create_url(),
            data={"email": "new@test.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @with_internal_auth
    def test_create_with_invalid_payload_returns_validation_error(self):
        # Missing required email (BasicUserSerializer requires email)
        response = self.client.post(
            self._create_url(), data={}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @with_internal_auth
    def test_create_with_valid_payload_creates_user(self):
        response = self.client.post(
            self._create_url(),
            data={
                "email": "fresh@test.com",
                "first_name": "Fresh",
                "last_name": "User",
                "photo_url": "http://example.com/p.png",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(email="fresh@test.com")
        self.assertEqual(user.first_name, "Fresh")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.photo_url, "http://example.com/p.png")


class TestInternalUserViewSetLanguage(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, token = create_user_and_token("internal-lang")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

    def test_language_endpoint_updates_user_language(self):
        url = reverse("user_internal-language")
        response = self.client.put(
            f"{url}?email=lang-user@test.com",
            data={"language": "es"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(email="lang-user@test.com")
        self.assertEqual(user.language, "es")
