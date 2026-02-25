from datetime import timedelta
from unittest.mock import patch

import pendulum
from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.external.rooms.serializers import RoomMetricsSerializer
from chats.apps.api.v1.rooms.serializers import RoomInfoSerializer
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import AutomaticMessage, Message
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


def create_agent_message(room, user, text, created_on=None):
    """
    Helper to create agent message and update denormalized fields.
    """
    msg = Message.objects.create(
        room=room, user=user, text=text, created_on=created_on or timezone.now()
    )
    # Update denormalized fields
    room.update_last_message(message=msg, user=user)
    room.refresh_from_db()
    return msg


def create_automatic_message(room, user, text, created_on=None):
    """
    Helper to create automatic message and update denormalized fields.
    """
    msg = Message.objects.create(
        room=room, user=user, text=text, created_on=created_on or timezone.now()
    )
    AutomaticMessage.objects.create(room=room, message=msg)
    # Update denormalized field
    Room.objects.filter(pk=room.pk).update(automatic_message_sent_at=msg.created_on)
    room.refresh_from_db()
    return msg


@patch(
    "chats.apps.api.v1.external.rooms.serializers.is_feature_active",
    return_value=True,
)
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

    def test_first_user_message_returns_none_when_no_agent_messages(self, mock_ff):
        """Should return None when room has no agent messages"""
        Message.objects.create(room=self.room, contact=self.contact, text="Hello")

        serializer = RoomMetricsSerializer(self.room)
        self.assertIsNone(serializer.data["first_user_message"])

    def test_first_user_message_returns_date_when_agent_message_exists(self, mock_ff):
        """Should return the date of first agent message"""
        first_msg_time = timezone.now() - timedelta(hours=2)
        second_msg_time = timezone.now() - timedelta(hours=1)

        create_agent_message(self.room, self.user, "First", created_on=first_msg_time)
        create_agent_message(self.room, self.user, "Second", created_on=second_msg_time)

        serializer = RoomMetricsSerializer(self.room)
        result = serializer.data["first_user_message"]

        self.assertIsNotNone(result)
        result_date = pendulum.parse(result)
        self.assertEqual(result_date.date(), first_msg_time.date())

    def test_first_user_message_ignores_contact_messages(self, mock_ff):
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
        result_date = pendulum.parse(result)
        self.assertEqual(result_date.date(), agent_msg_time.date())


@patch(
    "chats.apps.api.v1.external.rooms.serializers.is_feature_active",
    return_value=True,
)
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

    def test_automatic_message_sent_at_returns_none_when_no_automatic_message(
        self, mock_ff
    ):
        """Should return None when room has no automatic message"""
        serializer = RoomMetricsSerializer(self.room)
        self.assertIsNone(serializer.data["automatic_message_sent_at"])

    def test_automatic_message_sent_at_returns_date_when_exists(self, mock_ff):
        """Should return the date when automatic message was sent"""
        create_automatic_message(self.room, self.user, "Auto msg")

        serializer = RoomMetricsSerializer(self.room)
        result = serializer.data["automatic_message_sent_at"]

        self.assertIsNotNone(result)

    def test_time_to_send_automatic_message_returns_none_when_no_automatic_message(
        self, mock_ff
    ):
        """Should return None when no automatic message exists"""
        serializer = RoomMetricsSerializer(self.room)
        self.assertIsNone(serializer.data["time_to_send_automatic_message"])

    def test_time_to_send_automatic_message_calculates_correctly(self, mock_ff):
        """Should calculate time between first_user_assigned_at and automatic message"""
        msg_time = self.room.first_user_assigned_at + timedelta(minutes=5)
        create_automatic_message(self.room, self.user, "Auto msg", created_on=msg_time)

        serializer = RoomMetricsSerializer(self.room)
        result = serializer.data["time_to_send_automatic_message"]

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 300, delta=5)

    def test_time_to_send_automatic_message_returns_none_without_first_user_assigned_at(
        self, mock_ff
    ):
        """Should return None when room has no first_user_assigned_at"""
        # Use update() to bypass save() which auto-sets first_user_assigned_at
        Room.objects.filter(pk=self.room.pk).update(first_user_assigned_at=None)
        self.room.refresh_from_db()

        create_automatic_message(self.room, self.user, "Auto msg")

        serializer = RoomMetricsSerializer(self.room)
        self.assertIsNone(serializer.data["time_to_send_automatic_message"])


@patch(
    "chats.apps.api.v1.rooms.serializers.is_feature_active",
    return_value=True,
)
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

    def test_first_user_message_sent_at_returns_none_when_no_messages(self, mock_ff):
        """Should return None when room has no agent messages"""
        serializer = RoomInfoSerializer(self.room)
        self.assertIsNone(serializer.data["first_user_message_sent_at"])

    def test_first_user_message_sent_at_returns_datetime_when_exists(self, mock_ff):
        """Should return datetime of first agent message"""
        msg_time = timezone.now() - timedelta(hours=1)
        create_agent_message(self.room, self.user, "Test", created_on=msg_time)

        serializer = RoomInfoSerializer(self.room)
        result = serializer.data["first_user_message_sent_at"]

        self.assertIsNotNone(result)


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
        msg = Message.objects.create(room=self.room, user=self.user, text="Auto msg")
        AutomaticMessage.objects.create(room=self.room, message=msg)
        self.room.refresh_from_db()

        self.assertIsNone(self.room.automatic_message_sent_at)
        sent_at = self.room.get_automatic_message_sent_at()
        self.assertIsNotNone(sent_at)
        self.assertEqual(sent_at, msg.created_on)

    def test_denormalized_field_takes_priority_over_query(self):
        """When denormalized field is set, should use it instead of querying"""
        msg = Message.objects.create(room=self.room, user=self.user, text="Auto msg")
        AutomaticMessage.objects.create(room=self.room, message=msg)

        custom_time = timezone.now() - timedelta(hours=5)
        Room.objects.filter(pk=self.room.pk).update(
            automatic_message_sent_at=custom_time
        )
        self.room.refresh_from_db()

        sent_at = self.room.get_automatic_message_sent_at()
        self.assertEqual(sent_at, custom_time)
