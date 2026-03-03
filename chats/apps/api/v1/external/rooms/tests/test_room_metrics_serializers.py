from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.external.rooms.serializers import RoomMetricsSerializer
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import AutomaticMessage, Message
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


def create_automatic_message(room, user, text, created_on=None):
    msg = Message.objects.create(
        room=room, user=user, text=text, created_on=created_on or timezone.now()
    )
    AutomaticMessage.objects.create(room=room, message=msg)
    Room.objects.filter(pk=room.pk).update(automatic_message_sent_at=msg.created_on)
    room.refresh_from_db()
    return msg


class TestRoomMetricsSerializerAutomaticMessage(TestCase):
    """Tests for automatic_message_sent_at and time_to_send_automatic_message"""

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
            first_user_assigned_at=timezone.now() - timedelta(minutes=10),
        )

    def test_automatic_message_sent_at_returns_none_when_no_automatic_message(self):
        """Should return None when room has no automatic message"""
        serializer = RoomMetricsSerializer(self.room)
        self.assertIsNone(serializer.data["automatic_message_sent_at"])

    def test_automatic_message_sent_at_returns_date_when_exists(self):
        """Should return the date when automatic message was sent"""
        create_automatic_message(self.room, self.user, "Auto msg")
        serializer = RoomMetricsSerializer(self.room)
        result = serializer.data["automatic_message_sent_at"]
        self.assertIsNotNone(result)

    def test_time_to_send_automatic_message_returns_none_when_no_automatic_message(
        self,
    ):
        """Should return None when no automatic message exists"""
        serializer = RoomMetricsSerializer(self.room)
        self.assertIsNone(serializer.data["time_to_send_automatic_message"])

    def test_time_to_send_automatic_message_calculates_correctly(self):
        """Should calculate time between first_user_assigned_at and automatic message"""
        msg_time = self.room.first_user_assigned_at + timedelta(minutes=5)
        create_automatic_message(self.room, self.user, "Auto msg", created_on=msg_time)
        serializer = RoomMetricsSerializer(self.room)
        result = serializer.data["time_to_send_automatic_message"]
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 300, delta=5)

    def test_time_to_send_automatic_message_returns_none_without_first_user_assigned_at(
        self,
    ):
        """Should return None when room has no first_user_assigned_at"""
        Room.objects.filter(pk=self.room.pk).update(first_user_assigned_at=None)
        self.room.refresh_from_db()
        create_automatic_message(self.room, self.user, "Auto msg")
        serializer = RoomMetricsSerializer(self.room)
        self.assertIsNone(serializer.data["time_to_send_automatic_message"])

    def test_automatic_message_fallback_when_denormalized_field_is_empty(self):
        """Should fallback to AutomaticMessage query when field is not populated"""
        msg = Message.objects.create(
            room=self.room, user=self.user, text="Auto msg"
        )
        AutomaticMessage.objects.create(room=self.room, message=msg)
        self.room.refresh_from_db()

        self.assertIsNone(self.room.automatic_message_sent_at)
        sent_at = self.room.get_automatic_message_sent_at()
        self.assertIsNotNone(sent_at)
        self.assertEqual(sent_at, msg.created_on)

    def test_denormalized_field_takes_priority_over_query(self):
        """When denormalized field is set, should use it instead of querying"""
        msg = Message.objects.create(
            room=self.room, user=self.user, text="Auto msg"
        )
        AutomaticMessage.objects.create(room=self.room, message=msg)

        custom_time = timezone.now() - timedelta(hours=5)
        Room.objects.filter(pk=self.room.pk).update(
            automatic_message_sent_at=custom_time
        )
        self.room.refresh_from_db()

        sent_at = self.room.get_automatic_message_sent_at()
        self.assertEqual(sent_at, custom_time)
