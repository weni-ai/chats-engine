from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.external.rooms.serializers import RoomMetricsSerializer
from chats.apps.api.v1.rooms.serializers import RoomInfoSerializer
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


def create_agent_message(room, user, text, created_on=None):
    msg = Message.objects.create(
        room=room, user=user, text=text, created_on=created_on or timezone.now()
    )
    room.update_last_message(message=msg, user=user)
    room.refresh_from_db()
    return msg


class TestRoomMetricsSerializerFirstUserMessage(TestCase):
    """Tests for get_first_user_message in RoomMetricsSerializer"""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create(email="agent@test.com")
        self.contact = Contact.objects.create(name="Test Contact", external_id="123")
        self.room = Room.objects.create(
            queue=self.queue,
            user=self.user,
            contact=self.contact,
        )

    def test_first_user_message_returns_none_when_no_agent_messages(self):
        """Should return None when room has no agent messages"""
        Message.objects.create(room=self.room, contact=self.contact, text="Hello")
        serializer = RoomMetricsSerializer(self.room)
        self.assertIsNone(serializer.data["first_user_message"])

    def test_first_user_message_returns_date_when_agent_message_exists(self):
        """Should return the date of first agent message"""
        first_msg_time = timezone.now() - timedelta(hours=2)
        second_msg_time = timezone.now() - timedelta(hours=1)

        create_agent_message(self.room, self.user, "First", created_on=first_msg_time)
        create_agent_message(self.room, self.user, "Second", created_on=second_msg_time)

        serializer = RoomMetricsSerializer(self.room)
        result = serializer.data["first_user_message"]
        self.assertIsNotNone(result)

    def test_first_user_message_ignores_contact_messages(self):
        """Should only consider agent messages, not contact messages"""
        contact_msg_time = timezone.now() - timedelta(hours=3)
        agent_msg_time = timezone.now() - timedelta(hours=1)

        Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="Contact first",
            created_on=contact_msg_time,
        )
        create_agent_message(
            self.room, self.user, "Agent later", created_on=agent_msg_time
        )

        serializer = RoomMetricsSerializer(self.room)
        result = serializer.data["first_user_message"]
        self.assertIsNotNone(result)

    def test_fallback_when_denormalized_field_is_empty(self):
        """Should fallback to query when first_agent_message_at is not populated"""
        msg = Message.objects.create(
            room=self.room, user=self.user, text="Test"
        )
        self.room.refresh_from_db()

        self.assertIsNone(self.room.first_agent_message_at)
        result = self.room.get_first_agent_message_at()
        self.assertIsNotNone(result)
        self.assertEqual(result, msg.created_on)

    def test_denormalized_field_takes_priority_over_query(self):
        """When denormalized field is set, should use it instead of querying"""
        Message.objects.create(room=self.room, user=self.user, text="Test")

        custom_time = timezone.now() - timedelta(hours=5)
        Room.objects.filter(pk=self.room.pk).update(
            first_agent_message_at=custom_time
        )
        self.room.refresh_from_db()

        result = self.room.get_first_agent_message_at()
        self.assertEqual(result, custom_time)

    def test_update_last_message_populates_first_agent_message_at(self):
        """update_last_message should set first_agent_message_at on first agent message"""
        msg = Message.objects.create(
            room=self.room, user=self.user, text="First"
        )
        self.room.update_last_message(message=msg, user=self.user)
        self.room.refresh_from_db()

        self.assertEqual(self.room.first_agent_message_at, msg.created_on)

    def test_update_last_message_does_not_overwrite_first_agent_message_at(self):
        """update_last_message should NOT overwrite first_agent_message_at on subsequent messages"""
        msg1 = Message.objects.create(
            room=self.room, user=self.user, text="First",
            created_on=timezone.now() - timedelta(hours=2),
        )
        self.room.update_last_message(message=msg1, user=self.user)
        self.room.refresh_from_db()
        first_value = self.room.first_agent_message_at

        msg2 = Message.objects.create(
            room=self.room, user=self.user, text="Second",
            created_on=timezone.now() - timedelta(hours=1),
        )
        self.room.update_last_message(message=msg2, user=self.user)
        self.room.refresh_from_db()

        self.assertEqual(self.room.first_agent_message_at, first_value)


class TestRoomInfoSerializerFirstUserMessage(TestCase):
    """Tests for get_first_user_message_sent_at in RoomInfoSerializer"""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create(email="agent@test.com")
        self.room = Room.objects.create(queue=self.queue, user=self.user)

    def test_first_user_message_sent_at_returns_none_when_no_messages(self):
        """Should return None when room has no agent messages"""
        serializer = RoomInfoSerializer(self.room)
        self.assertIsNone(serializer.data["first_user_message_sent_at"])

    def test_first_user_message_sent_at_returns_datetime_when_exists(self):
        """Should return datetime of first agent message"""
        msg_time = timezone.now() - timedelta(hours=1)
        create_agent_message(self.room, self.user, "Test", created_on=msg_time)

        serializer = RoomInfoSerializer(self.room)
        result = serializer.data["first_user_message_sent_at"]
        self.assertIsNotNone(result)
