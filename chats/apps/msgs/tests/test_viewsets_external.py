from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.rooms.models import Room

class MsgsExternalTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_app.json']

    def setUp(self) -> None:
        self.room = Room.objects.get(uuid="090da6d1-959e-4dea-994a-41bf0d38ba26")

    def test_create_external_msgs(self):
        """
        Verify if the external message endpoint are creating messages correctly.
        """
        url = reverse("external_message-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380")
        data = {
            "room": self.room.uuid,
            "text": "olá.",
            "direction": "incoming",
            "attachments": [
            {
                "content_type": "string",
                "url": "http://example.com"
            }
            ],
        }
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
