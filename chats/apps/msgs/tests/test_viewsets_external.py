from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone
from django.utils.timezone import timedelta

from chats.apps.msgs.models import Message
from chats.apps.rooms.models import Room


class MsgsExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.room = Room.objects.get(uuid="090da6d1-959e-4dea-994a-41bf0d38ba26")

    def _remove_user(self):
        room = self.room
        room.user = None
        room.save()
        return room

    def _update_default_message(self, default_message):
        queue = self.room.queue
        queue.default_message = default_message
        queue.save()
        return queue

    def _request_create_message(self, direction: str = "incoming", created_on=None):
        url = reverse("external_message-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "room": self.room.uuid,
            "text": "olá.",
            "direction": direction,
            "attachments": [{"content_type": "string", "url": "http://example.com"}],
            "created_on": created_on,
        }
        return client.post(url, data=data, format="json")

    def test_create_external_msgs(self):
        """
        Verify if the external message endpoint are creating messages correctly.
        """
        created_on = timezone.now() - timedelta(days=5)
        response = self._request_create_message(created_on=created_on)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)

        msg = Message.objects.filter(uuid=response.data["uuid"]).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.created_on, created_on)

    def test_create_external_msgs_with_null_created_on(self):
        """
        Verify if the external message endpoint are creating messages correctly
        when passing a null created_on.
        """
        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)

        msg = Message.objects.filter(uuid=response.data["uuid"]).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.created_on.date(), timezone.now().date())

    def test_create_with_default_message_room_without_user(self):
        _ = self._remove_user()

        queue = self._update_default_message(default_message="DEFAULT MESSAGE")

        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 4)
        self.assertEqual(
            self.room.messages.order_by("-created_on").first().text,
            queue.default_message,
        )

    def test_create_with_default_message_room_with_user(self):
        queue = self._update_default_message(default_message="DEFAULT MESSAGE")

        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)
        self.assertNotEqual(
            self.room.messages.order_by("-created_on").first().text,
            queue.default_message,
        )

    def test_create_without_default_message_room_without_user(self):
        room = self._remove_user()
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

    def test_create_with_empty_default_message_room_without_user(self):
        _ = self._remove_user()

        queue = self._update_default_message(default_message="")

        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)
        self.assertNotEqual(
            self.room.messages.order_by("-created_on").first().text,
            queue.default_message,
        )

    def test_create_outgoing_with_default_message_room_without_user(self):
        _ = self._remove_user()

        queue = self._update_default_message(default_message="DEFAULT MESSAGE")

        response = self._request_create_message(direction="outgoing")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)
        self.assertNotEqual(
            self.room.messages.order_by("-created_on").first().text,
            queue.default_message,
        )
