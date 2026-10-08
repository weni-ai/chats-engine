from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import ChatMessageReplyIndex, Message
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room, RoomNote
from chats.apps.sectors.models import Sector

User = get_user_model()


class BaseInternalRoomHistoryTest(APITestCase):
    """Shared setup for the internal room history endpoint."""

    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(email="internal@vtex.com")
        self.agent = User.objects.create_user(
            email="agent@test.com",
            password="testpass123",
            first_name="Ana",
            last_name="Agent",
        )
        self.contact = Contact.objects.create(name="Maria Cliente")

        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
            is_active=True,
            project_uuid=str(self.project.uuid),
        )
        self.open_room = Room.objects.create(
            contact=Contact.objects.create(name="Open Customer"),
            queue=self.queue,
            user=self.agent,
            is_active=True,
            project_uuid=str(self.project.uuid),
        )

        self.client.force_authenticate(self.user)

    def tearDown(self):
        cache.clear()

    def close_room(self, room=None):
        target = room or self.room
        Room.objects.filter(pk=target.pk).update(is_active=False)
        target.refresh_from_db()
        return target

    @property
    def url(self):
        return reverse("internal_room_messages-list")

    def get(self, params=None):
        return self.client.get(self.url, params or {})


class TestInternalRoomHistoryAuth(BaseInternalRoomHistoryTest):
    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        self.close_room()
        response = self.get({"room": str(self.room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_without_internal_permission_returns_403(self):
        self.close_room()
        response = self.get({"room": str(self.room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_valid_internal_permission_returns_200(self):
        self.close_room()
        response = self.get({"room": str(self.room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestInternalRoomHistoryQueryValidation(BaseInternalRoomHistoryTest):
    @with_internal_auth
    def test_missing_room_returns_400(self):
        response = self.get()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("room", response.data)

    @with_internal_auth
    def test_invalid_room_uuid_returns_400(self):
        response = self.get({"room": "not-a-uuid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("room", response.data)

    @with_internal_auth
    def test_unknown_room_returns_404(self):
        response = self.get({"room": "00000000-0000-0000-0000-000000000000"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @with_internal_auth
    def test_open_room_returns_403_with_message(self):
        response = self.get({"room": str(self.open_room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertIn("closed rooms", str(response.data["detail"]).lower())

    @with_internal_auth
    def test_closed_room_returns_200(self):
        self.close_room()
        response = self.get({"room": str(self.room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestInternalRoomHistoryPayloadShape(BaseInternalRoomHistoryTest):
    @with_internal_auth
    def test_response_returns_documented_fields(self):
        Message.objects.create(room=self.room, contact=self.contact, text="Hello!")
        Message.objects.create(
            room=self.room, user=self.agent, text="Hi, how can I help?"
        )
        self.close_room()

        response = self.get({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 2)

        expected_fields = {
            "user",
            "contact",
            "created_on",
            "replied_message",
            "media",
            "is_automatic_message",
            "uuid",
            "text",
        }
        for item in response.data["results"]:
            self.assertEqual(set(item.keys()), expected_fields)


class TestInternalRoomHistoryInternalNoteFilter(BaseInternalRoomHistoryTest):
    @with_internal_auth
    def test_internal_note_messages_are_excluded(self):
        Message.objects.create(room=self.room, contact=self.contact, text="Visible")
        hidden_msg = Message.objects.create(room=self.room, user=self.agent, text="")
        RoomNote.objects.create(
            room=self.room,
            user=self.agent,
            text="Internal observation",
            message=hidden_msg,
        )
        self.close_room()

        response = self.get({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        only_item = response.data["results"][0]
        self.assertIsNone(only_item["user"])
        self.assertIsNotNone(only_item["contact"])
        self.assertEqual(only_item["contact"]["uuid"], str(self.contact.uuid))


class TestInternalRoomHistoryRepliedMessage(BaseInternalRoomHistoryTest):
    @with_internal_auth
    def test_replied_message_resolves_through_reply_index(self):
        original = Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="What are your business hours?",
            external_id="ext-123",
        )
        ChatMessageReplyIndex.objects.create(external_id="ext-123", message=original)
        Message.objects.create(
            room=self.room,
            user=self.agent,
            text="We operate from 9am to 6pm",
            metadata={"context": {"id": "ext-123"}},
        )
        self.close_room()

        response = self.get({"room": str(self.room.uuid)})

        target = next(
            (m for m in response.data["results"] if m["replied_message"] is not None),
            None,
        )
        self.assertIsNotNone(target)
        self.assertEqual(target["replied_message"]["uuid"], str(original.uuid))
        self.assertEqual(
            target["replied_message"]["text"], "What are your business hours?"
        )
        self.assertEqual(set(target["replied_message"].keys()), {"uuid", "text"})


class TestInternalRoomHistoryPagination(BaseInternalRoomHistoryTest):
    @with_internal_auth
    def test_pagination_keys_present(self):
        Message.objects.create(room=self.room, contact=self.contact, text="hello")
        self.close_room()

        response = self.get({"room": str(self.room.uuid)})

        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)


class TestInternalRoomHistoryCaching(BaseInternalRoomHistoryTest):
    @with_internal_auth
    def test_second_identical_request_returns_cached_payload(self):
        Message.objects.create(room=self.room, contact=self.contact, text="first call")
        self.close_room()

        first = self.get({"room": str(self.room.uuid)})
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        first_count = len(first.data["results"])

        Room.objects.filter(pk=self.room.pk).update(is_active=True)
        self.room.refresh_from_db()
        Message.objects.create(
            room=self.room, contact=self.contact, text="added after cache"
        )
        self.close_room()

        second = self.get({"room": str(self.room.uuid)})
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(len(second.data["results"]), first_count)

        cache.clear()
        third = self.get({"room": str(self.room.uuid)})
        self.assertEqual(len(third.data["results"]), first_count + 1)

    @with_internal_auth
    @override_settings(ROOM_HISTORY_CACHE_TTL=123)
    def test_uses_room_history_cache_ttl_from_settings(self):
        Message.objects.create(room=self.room, contact=self.contact, text="payload")
        self.close_room()

        with mock.patch(
            "chats.apps.api.v1.internal.msgs.viewsets.cache.set"
        ) as mocked_set, mock.patch(
            "chats.apps.api.v1.internal.msgs.viewsets.is_reply_core_fallback_active",
            return_value=False,
        ):
            response = self.get({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_set.assert_called_once()
        args, _kwargs = mocked_set.call_args
        self.assertEqual(args[2], 123)
