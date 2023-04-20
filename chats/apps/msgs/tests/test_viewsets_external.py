from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.rooms.models import Room


class MsgsExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.room = Room.objects.get(uuid="090da6d1-959e-4dea-994a-41bf0d38ba26")

    def _request_create_message(self):
        url = reverse("external_message-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "room": self.room.uuid,
            "text": "olá.",
            "direction": "incoming",
            "attachments": [{"content_type": "string", "url": "http://example.com"}],
        }
        return client.post(url, data=data, format="json")

    def test_create_external_msgs(self):
        """
        Verify if the external message endpoint are creating messages correctly.
        """
        response = self._request_create_message()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)

    def test_create_with_default_message_room_without_user(self):
        room = self.room
        room.user = None
        room.save()

        queue = room.queue
        queue.default_message = "DEFAULT MESSAGE"
        queue.save()

        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 4)
        self.assertEqual(
            self.room.messages.order_by("-created_on").first().text,
            queue.default_message,
        )

    def test_create_with_default_message_room_with_user(self):
        queue = self.room.queue
        queue.default_message = "DEFAULT MESSAGE"
        queue.save()

        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)
        self.assertNotEqual(
            self.room.messages.order_by("-created_on").first().text,
            queue.default_message,
        )

    def test_create_without_default_message_room_without_user(self):
        room = self.room
        room.user = None
        room.save()

        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)
        self.assertNotEqual(
            self.room.messages.order_by("-created_on").first().text,
            room.queue.default_message,
        )

    def test_create_without_default_message_room_with_user(self):
        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)
        self.assertNotEqual(
            self.room.messages.order_by("-created_on").first().text,
            self.room.queue.default_message,
        )
