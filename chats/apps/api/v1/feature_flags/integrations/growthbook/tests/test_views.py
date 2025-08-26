import json
from unittest.mock import patch

from django.urls import reverse

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APITestCase
from rest_framework.response import Response


class TestGrowthbookWebhook(APITestCase):
    def receive_webhook(self, body: str) -> Response:
        url = reverse("growthbook_webhook-list")

        return self.client.post(url, body, format="json")

    @patch(
        "chats.apps.api.v1.feature_flags.integrations.growthbook.auth.GrowthbookWebhookSecretAuthentication.authenticate"
    )
    @patch(
        "chats.apps.feature_flags.integrations.growthbook.tasks.update_growthbook_feature_flags.delay"
    )
    def test_cannot_receive_webhook_when_authentication_fails(
        self, mock_update_growthbook_feature_flags, mock_authenticate
    ):
        mock_authenticate.side_effect = AuthenticationFailed("Authentication failed")
        mock_update_growthbook_feature_flags.return_value = None

        body = json.dumps({"test": "test"})

        response = self.receive_webhook(body)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        mock_update_growthbook_feature_flags.assert_not_called()

    @patch(
        "chats.apps.api.v1.feature_flags.integrations.growthbook.auth.GrowthbookWebhookSecretAuthentication.authenticate"
    )
    @patch(
        "chats.apps.feature_flags.integrations.growthbook.tasks.update_growthbook_feature_flags.delay"
    )
    def test_can_receive_webhook_when_authentication_succeeds(
        self, mock_update_growthbook_feature_flags, mock_authenticate
    ):
        mock_authenticate.return_value = (None, None)
        mock_update_growthbook_feature_flags.return_value = None

        body = json.dumps({"test": "test"})

        response = self.receive_webhook(body)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_update_growthbook_feature_flags.assert_called_once()
