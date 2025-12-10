import json
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.test import APITestCase


class TestGrowthbookWebhook(APITestCase):
    def receive_webhook(self, body: str) -> Response:
        url = reverse("growthbook_webhook-list")

        return self.client.post(url, body, format="json")

    @patch(
        "chats.apps.api.v1.feature_flags.integrations.growthbook.auth."
        "GrowthbookWebhookSecretAuthentication.authenticate"
    )
    def test_cannot_receive_webhook_when_authentication_fails(self, mock_authenticate):
        mock_authenticate.side_effect = AuthenticationFailed("Authentication failed")

        body = json.dumps({"test": "test"})

        response = self.receive_webhook(body)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(
        "chats.apps.api.v1.feature_flags.integrations.growthbook.auth."
        "GrowthbookWebhookSecretAuthentication.authenticate"
    )
    def test_can_receive_webhook_when_authentication_succeeds(self, mock_authenticate):
        mock_authenticate.return_value = (None, None)

        body = json.dumps({"test": "test"})

        response = self.receive_webhook(body)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
