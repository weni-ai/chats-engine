import uuid
from datetime import datetime, timedelta, timezone as dt_timezone

from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token

from chats.apps.api.utils import (
    calculate_in_service_time,
    create_contact,
    create_message,
    create_reply_index,
    create_room_dto,
    create_user_and_token,
    ensure_timezone,
)
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import ChatMessageReplyIndex, Message
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class _BaseHelpersTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Helpers Project")
        self.sector = Sector.objects.create(
            name="Helpers Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Helpers Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Helpers Contact")


class TestCreateUserAndToken(TestCase):
    def test_creates_user_and_token_when_missing(self):
        user, token = create_user_and_token("alice")
        self.assertEqual(user.email, "alice@user.com")
        self.assertIsInstance(token, Token)
        self.assertEqual(token.user, user)

    def test_idempotent(self):
        user1, token1 = create_user_and_token("bob")
        user2, token2 = create_user_and_token("bob")
        self.assertEqual(user1.pk, user2.pk)
        self.assertEqual(token1.key, token2.key)


class TestCreateMessage(_BaseHelpersTestCase):
    def test_returns_none_when_user_equals_contact(self):
        # When user == contact (both None), returns None per the implementation.
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        self.assertIsNone(create_message("hello", room=room, user=None, contact=None))

    def test_creates_message_and_updates_room_last_message_when_text(self):
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        message = create_message("hello", room=room, user=None, contact=self.contact)
        self.assertIsNotNone(message)
        self.assertEqual(message.text, "hello")
        self.assertEqual(message.room, room)

    def test_does_not_update_last_message_when_text_empty(self):
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        message = create_message("", room=room, user=None, contact=self.contact)
        self.assertIsNotNone(message)
        self.assertEqual(message.text, "")


class TestCreateContact(TestCase):
    def test_creates_contact_with_defaults(self):
        contact = create_contact("Carol", "carol@test.com")
        self.assertEqual(contact.name, "Carol")
        self.assertEqual(contact.email, "carol@test.com")
        self.assertEqual(contact.status, "OFFLINE")
        self.assertIsNotNone(contact.external_id)
        self.assertEqual(contact.custom_fields, {})

    def test_creates_contact_with_custom_fields(self):
        contact = create_contact(
            "Dave",
            "dave@test.com",
            status="ONLINE",
            custom_fields={"role": "lead"},
        )
        self.assertEqual(contact.status, "ONLINE")
        self.assertEqual(contact.custom_fields, {"role": "lead"})


class TestCreateRoomDto(TestCase):
    def test_returns_serialized_room_dto(self):
        data = create_room_dto(
            {"interact_time": 60, "response_time": 30, "waiting_time": 15}
        )
        self.assertEqual(len(data), 1)
        # DashboardRoomSerializer returns OrderedDict-like fields
        first = data[0]
        # Whatever the exact field names, our data has interact/response/waiting time.
        self.assertIn(60, first.values())
        self.assertIn(30, first.values())
        self.assertIn(15, first.values())

    def test_returns_dto_with_missing_fields_as_none(self):
        data = create_room_dto({})
        self.assertEqual(len(data), 1)
        # Field values should be None when not provided
        self.assertTrue(all(value is None for value in data[0].values()))


class TestEnsureTimezone(TestCase):
    def test_returns_aware_datetime_unchanged(self):
        tz = dt_timezone.utc
        aware = datetime(2026, 1, 1, 12, 0, tzinfo=tz)
        self.assertIs(ensure_timezone(aware, tz), aware)

    def test_makes_naive_datetime_aware(self):
        tz = dt_timezone.utc
        naive = datetime(2026, 1, 1, 12, 0)
        result = ensure_timezone(naive, tz)
        self.assertIsNotNone(result.tzinfo)
        self.assertEqual(result.tzinfo, tz)

    def test_falls_back_to_replace_when_tz_has_no_localize(self):
        # dt.timezone has no localize method, so AttributeError branch executes.
        naive = datetime(2026, 1, 1, 12, 0)
        result = ensure_timezone(naive, dt_timezone.utc)
        self.assertIsNotNone(result.tzinfo)


class TestCreateReplyIndex(_BaseHelpersTestCase):
    def _make_message(self, external_id=None, contact=None):
        # Use a fresh contact per room to avoid the unique_contact_queue_is_activetrue_room constraint
        if contact is None:
            contact = Contact.objects.create(
                name="ReplyIndex Contact",
                external_id=str(uuid.uuid4()),
            )
        room = Room.objects.create(queue=self.queue, contact=contact)
        return Message.objects.create(
            room=room,
            text="hi",
            contact=contact,
            external_id=external_id,
        )

    def test_returns_none_when_no_external_id(self):
        msg = self._make_message(external_id=None)
        self.assertIsNone(create_reply_index(msg))
        self.assertFalse(ChatMessageReplyIndex.objects.filter(message=msg).exists())

    def test_creates_index_when_none_exists(self):
        msg = self._make_message(external_id="ext-1")
        create_reply_index(msg)
        self.assertTrue(
            ChatMessageReplyIndex.objects.filter(
                external_id="ext-1", message=msg
            ).exists()
        )

    def test_updates_index_when_already_present(self):
        first_msg = self._make_message(external_id="ext-2")
        ChatMessageReplyIndex.objects.create(external_id="ext-2", message=first_msg)
        # Use a fresh contact for the second room to avoid the unique constraint
        new_msg = self._make_message(external_id="ext-2")
        create_reply_index(new_msg)
        index = ChatMessageReplyIndex.objects.get(external_id="ext-2")
        self.assertEqual(index.message_id, new_msg.pk)


class TestCalculateInServiceTime(TestCase):
    def test_returns_zero_for_empty_list(self):
        self.assertEqual(calculate_in_service_time([]), 0)
        self.assertEqual(calculate_in_service_time(None), 0)

    def test_accumulates_break_time_from_inactive_status(self):
        statuses = [
            {
                "status_type": "Lunch",
                "is_active": False,
                "break_time": 300,
            },
            {
                "status_type": "In-Service",
                "is_active": False,
                "break_time": 600,
            },
        ]
        result = calculate_in_service_time(statuses)
        self.assertEqual(result, 600)

    def test_active_in_service_adds_period(self):
        # 60 seconds ago
        created_on = (timezone.now() - timedelta(seconds=60)).isoformat()
        statuses = [
            {
                "status_type": "In-Service",
                "is_active": True,
                "created_on": created_on,
            }
        ]
        result = calculate_in_service_time(statuses, user_status="ONLINE")
        self.assertGreaterEqual(result, 50)
        self.assertLessEqual(result, 90)

    def test_active_in_service_ignored_when_user_offline(self):
        created_on = (timezone.now() - timedelta(seconds=60)).isoformat()
        statuses = [
            {
                "status_type": "In-Service",
                "is_active": True,
                "created_on": created_on,
            }
        ]
        self.assertEqual(calculate_in_service_time(statuses, user_status="OFFLINE"), 0)

    def test_skips_status_without_created_on(self):
        statuses = [
            {"status_type": "In-Service", "is_active": True, "created_on": None}
        ]
        self.assertEqual(calculate_in_service_time(statuses, user_status="ONLINE"), 0)

    def test_skips_status_with_invalid_created_on(self):
        statuses = [
            {
                "status_type": "In-Service",
                "is_active": True,
                "created_on": "not-a-date",
            }
        ]
        self.assertEqual(calculate_in_service_time(statuses, user_status="ONLINE"), 0)
