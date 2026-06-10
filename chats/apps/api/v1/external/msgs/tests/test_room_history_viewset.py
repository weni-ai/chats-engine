from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.v1.external.msgs.viewsets import RoomHistoryMessagesViewSet
from chats.apps.api.v1.external.throttling import (
    ExternalRoomHistoryHourRateThrottle,
    ExternalRoomHistoryMinuteRateThrottle,
    ExternalRoomHistorySecondRateThrottle,
)
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import (
    ChatMessageReplyIndex,
    Message,
    MessageMedia,
)
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room, RoomNote
from chats.apps.sectors.models import Sector

User = get_user_model()

NO_THROTTLE_RATES = {
    "DEFAULT_THROTTLE_RATES": {
        "external_room_history_second": None,
        "external_room_history_minute": None,
        "external_room_history_hour": None,
    }
}


class BaseRoomHistoryTest(APITestCase):
    """Shared setup for the external room history endpoint."""

    def setUp(self):
        cache.clear()

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
        )
        self.open_room = Room.objects.create(
            contact=Contact.objects.create(name="Open Customer"),
            queue=self.queue,
            user=self.agent,
            is_active=True,
        )

    def tearDown(self):
        cache.clear()

    def close_room(self, room=None):
        """Close a room by bypassing the Message save validation."""
        target = room or self.room
        Room.objects.filter(pk=target.pk).update(is_active=False)
        target.refresh_from_db()
        return target

    @property
    def url(self):
        return reverse("external_room_messages-list")

    def auth(self, token=None):
        t = token or self.project.external_token.uuid
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {t}")

    def get(self, params=None):
        return self.client.get(self.url, params or {})


@override_settings(REST_FRAMEWORK=NO_THROTTLE_RATES)
class TestRoomHistoryAuth(BaseRoomHistoryTest):
    def test_unauthenticated_request_returns_401(self):
        self.close_room()
        response = self.get({"room": str(self.room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_bearer_token_returns_401(self):
        self.close_room()
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer 00000000-0000-0000-0000-000000000000"
        )
        response = self.get({"room": str(self.room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_bearer_token_is_rejected_by_project_admin_auth(self):
        self.close_room()
        self.client.credentials(HTTP_AUTHORIZATION="Token some-internal-token")
        response = self.get({"room": str(self.room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_valid_bearer_token_returns_200(self):
        self.close_room()
        self.auth()
        response = self.get({"room": str(self.room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(REST_FRAMEWORK=NO_THROTTLE_RATES)
class TestRoomHistoryQueryValidation(BaseRoomHistoryTest):
    def test_missing_room_returns_400(self):
        self.auth()
        response = self.get()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("room", response.data)

    def test_invalid_room_uuid_returns_400(self):
        self.auth()
        response = self.get({"room": "not-a-uuid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("room", response.data)

    def test_unknown_room_returns_404(self):
        self.auth()
        response = self.get({"room": "00000000-0000-0000-0000-000000000000"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_room_from_other_project_returns_404(self):
        other_project = Project.objects.create(name="Other", timezone="UTC")
        other_sector = Sector.objects.create(
            name="Other sector",
            project=other_project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other queue", sector=other_sector)
        other_room = Room.objects.create(
            contact=Contact.objects.create(name="Outside"),
            queue=other_queue,
            is_active=True,
        )
        self.close_room(other_room)

        self.auth()
        response = self.get({"room": str(other_room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(REST_FRAMEWORK=NO_THROTTLE_RATES)
class TestRoomHistoryClosedRoomRequirement(BaseRoomHistoryTest):
    def test_open_room_returns_403_with_message(self):
        self.auth()
        response = self.get({"room": str(self.open_room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertIn("closed rooms", str(response.data["detail"]).lower())

    def test_closed_room_returns_200(self):
        self.close_room()
        self.auth()
        response = self.get({"room": str(self.room.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(REST_FRAMEWORK=NO_THROTTLE_RATES)
class TestRoomHistoryPayloadShape(BaseRoomHistoryTest):
    def test_response_returns_documented_fields(self):
        Message.objects.create(
            room=self.room, contact=self.contact, text="Hello!"
        )
        Message.objects.create(
            room=self.room, user=self.agent, text="Hi, how can I help?"
        )
        self.close_room()

        self.auth()
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
        }
        for item in response.data["results"]:
            self.assertEqual(set(item.keys()), expected_fields)

    def test_user_payload_has_name_and_email_or_is_null(self):
        Message.objects.create(room=self.room, user=self.agent, text="From agent")
        Message.objects.create(
            room=self.room, contact=self.contact, text="From contact"
        )
        self.close_room()

        self.auth()
        response = self.get({"room": str(self.room.uuid)})

        agent_payload = None
        contact_payload = None
        for item in response.data["results"]:
            if item["user"] is not None:
                agent_payload = item
            else:
                contact_payload = item

        self.assertIsNotNone(agent_payload)
        self.assertEqual(set(agent_payload["user"].keys()), {"name", "email"})
        self.assertEqual(agent_payload["user"]["email"], self.agent.email)
        self.assertEqual(agent_payload["user"]["name"], "Ana Agent")

        self.assertIsNotNone(contact_payload)
        self.assertIsNone(contact_payload["user"])

    def test_contact_payload_has_uuid_and_name_or_is_null(self):
        Message.objects.create(room=self.room, user=self.agent, text="From agent")
        Message.objects.create(
            room=self.room, contact=self.contact, text="From contact"
        )
        self.close_room()

        self.auth()
        response = self.get({"room": str(self.room.uuid)})

        agent_payload = None
        contact_payload = None
        for item in response.data["results"]:
            if item["user"] is not None:
                agent_payload = item
            else:
                contact_payload = item

        self.assertIsNotNone(contact_payload)
        self.assertEqual(set(contact_payload["contact"].keys()), {"uuid", "name"})
        self.assertEqual(contact_payload["contact"]["uuid"], str(self.contact.uuid))
        self.assertEqual(contact_payload["contact"]["name"], self.contact.name)

        self.assertIsNotNone(agent_payload)
        self.assertIsNone(agent_payload["contact"])

    def test_media_is_serialized_with_url_content_type_and_created_on(self):
        msg = Message.objects.create(
            room=self.room, user=self.agent, text="See attached"
        )
        MessageMedia.objects.create(
            message=msg,
            content_type="image/jpeg",
            media_url="https://example.com/img.jpg",
        )
        self.close_room()

        self.auth()
        response = self.get({"room": str(self.room.uuid)})

        target = next(
            (
                m
                for m in response.data["results"]
                if m["media"] and len(m["media"]) > 0
            ),
            None,
        )
        self.assertIsNotNone(target)
        self.assertEqual(len(target["media"]), 1)
        self.assertEqual(
            set(target["media"][0].keys()), {"content_type", "url", "created_on"}
        )
        self.assertEqual(target["media"][0]["content_type"], "image/jpeg")

    def test_is_automatic_message_field_present(self):
        Message.objects.create(
            room=self.room, contact=self.contact, text="Regular message"
        )
        self.close_room()

        self.auth()
        response = self.get({"room": str(self.room.uuid)})

        self.assertEqual(response.data["results"][0]["is_automatic_message"], False)


@override_settings(REST_FRAMEWORK=NO_THROTTLE_RATES)
class TestRoomHistoryInternalNoteFilter(BaseRoomHistoryTest):
    def test_internal_note_messages_are_excluded(self):
        Message.objects.create(
            room=self.room, contact=self.contact, text="Visible"
        )
        hidden_msg = Message.objects.create(room=self.room, user=self.agent, text="")
        RoomNote.objects.create(
            room=self.room,
            user=self.agent,
            text="Internal observation",
            message=hidden_msg,
        )
        self.close_room()

        self.auth()
        response = self.get({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        only_item = response.data["results"][0]
        self.assertIsNone(only_item["user"])
        self.assertIsNotNone(only_item["contact"])
        self.assertEqual(only_item["contact"]["uuid"], str(self.contact.uuid))


@override_settings(REST_FRAMEWORK=NO_THROTTLE_RATES)
class TestRoomHistoryRepliedMessage(BaseRoomHistoryTest):
    def test_replied_message_resolves_through_reply_index(self):
        original = Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="What are your business hours?",
            external_id="ext-123",
        )
        ChatMessageReplyIndex.objects.create(
            external_id="ext-123", message=original
        )
        Message.objects.create(
            room=self.room,
            user=self.agent,
            text="We operate from 9am to 6pm",
            metadata={"context": {"id": "ext-123"}},
        )
        self.close_room()

        self.auth()
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

    def test_replied_message_is_none_when_index_missing(self):
        Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="Reply to nothing",
            metadata={"context": {"id": "non-existent-id"}},
        )
        self.close_room()

        self.auth()
        response = self.get({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["results"][0]["replied_message"])

    def test_replied_message_is_none_when_metadata_empty(self):
        Message.objects.create(
            room=self.room, contact=self.contact, text="empty meta", metadata={}
        )
        Message.objects.create(
            room=self.room, contact=self.contact, text="null meta", metadata=None
        )
        self.close_room()

        self.auth()
        response = self.get({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertIsNone(item["replied_message"])


@override_settings(REST_FRAMEWORK=NO_THROTTLE_RATES)
class TestRoomHistoryPagination(BaseRoomHistoryTest):
    def test_pagination_keys_present(self):
        Message.objects.create(
            room=self.room, contact=self.contact, text="hello"
        )
        self.close_room()

        self.auth()
        response = self.get({"room": str(self.room.uuid)})

        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)

    def test_pagination_caps_results_at_100(self):
        for i in range(120):
            Message.objects.create(
                room=self.room, contact=self.contact, text=f"msg {i}"
            )
        self.close_room()

        self.auth()
        response = self.get({"room": str(self.room.uuid)})

        self.assertEqual(len(response.data["results"]), 100)
        self.assertIsNotNone(response.data["next"])

    def test_page_size_query_param_cannot_exceed_100(self):
        for i in range(120):
            Message.objects.create(
                room=self.room, contact=self.contact, text=f"msg {i}"
            )
        self.close_room()

        self.auth()
        response = self.get({"room": str(self.room.uuid), "page_size": "500"})

        self.assertLessEqual(len(response.data["results"]), 100)


@override_settings(REST_FRAMEWORK=NO_THROTTLE_RATES)
class TestRoomHistoryCaching(BaseRoomHistoryTest):
    def test_second_identical_request_returns_cached_payload(self):
        Message.objects.create(
            room=self.room, contact=self.contact, text="first call"
        )
        self.close_room()

        self.auth()
        first = self.get({"room": str(self.room.uuid)})
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        first_count = len(first.data["results"])

        self.room.is_active = True
        self.room.save(update_fields=["is_active"])
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

    def test_cache_key_changes_with_cursor(self):
        for i in range(120):
            Message.objects.create(
                room=self.room, contact=self.contact, text=f"msg {i}"
            )
        self.close_room()

        self.auth()
        first = self.get({"room": str(self.room.uuid)})
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(first.data["next"])

        cursor_value = first.data["next"].split("cursor=")[-1]
        second = self.get({"room": str(self.room.uuid), "cursor": cursor_value})
        self.assertEqual(second.status_code, status.HTTP_200_OK)

        first_timestamps = {m["created_on"] for m in first.data["results"]}
        second_timestamps = {m["created_on"] for m in second.data["results"]}
        self.assertEqual(first_timestamps & second_timestamps, set())

    @override_settings(ROOM_HISTORY_CACHE_TTL=123)
    def test_uses_room_history_cache_ttl_from_settings(self):
        Message.objects.create(
            room=self.room, contact=self.contact, text="payload"
        )
        self.close_room()

        self.auth()
        with mock.patch(
            "chats.apps.api.v1.external.msgs.viewsets.cache.set"
        ) as mocked_set:
            response = self.get({"room": str(self.room.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_set.assert_called_once()
        args, _kwargs = mocked_set.call_args
        self.assertEqual(args[2], 123)


class TestRoomHistoryThrottleWiring(BaseRoomHistoryTest):
    def test_three_throttle_classes_are_attached(self):
        self.assertEqual(
            RoomHistoryMessagesViewSet.throttle_classes,
            [
                ExternalRoomHistorySecondRateThrottle,
                ExternalRoomHistoryMinuteRateThrottle,
                ExternalRoomHistoryHourRateThrottle,
            ],
        )

    def test_throttle_scopes_match_settings_keys(self):
        self.assertEqual(
            ExternalRoomHistorySecondRateThrottle.scope,
            "external_room_history_second",
        )
        self.assertEqual(
            ExternalRoomHistoryMinuteRateThrottle.scope,
            "external_room_history_minute",
        )
        self.assertEqual(
            ExternalRoomHistoryHourRateThrottle.scope,
            "external_room_history_hour",
        )
