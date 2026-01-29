from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.sectors.services import AutomaticMessagesService


def create_agent_message_with_denormalized_fields(room, user, text):
    """
    Helper to create agent message and update denormalized fields.
    """
    msg = Message.objects.create(room=room, user=user, text=text)
    # Update denormalized fields (simulating what update_last_message does)
    room.update_last_message(message=msg, user=user)
    room.refresh_from_db()
    return msg


@patch(
    "chats.apps.sectors.services.is_feature_active",
    return_value=True,
)
class TestAutomaticMessageBlockedByAgentMessages(TestCase):
    """
    Tests that automatic messages are NOT sent when room already has agent messages.
    This validates the `room.has_agent_messages` field check.
    """

    def setUp(self):
        self.service = AutomaticMessagesService()
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
            is_automatic_message_active=True,
            automatic_message_text="Welcome!",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create(email="agent@test.com")
        self.room = Room.objects.create(queue=self.queue)

    def test_automatic_message_blocked_when_agent_message_exists(self, mock_ff):
        """Automatic message should NOT be sent if agent already sent a message"""
        create_agent_message_with_denormalized_fields(
            self.room, self.user, "Hello!"
        )

        result = self.service.send_automatic_message(
            self.room, self.sector.automatic_message_text, self.user
        )

        self.assertFalse(result)

    def test_automatic_message_allowed_when_no_agent_messages(self, mock_ff):
        """Automatic message should be sent if no agent messages exist"""
        result = self.service.send_automatic_message(
            self.room, self.sector.automatic_message_text, self.user
        )

        self.assertTrue(result)

    def test_automatic_message_allowed_when_only_contact_messages(self, mock_ff):
        """Automatic message should be sent even if contact sent messages"""
        contact = Contact.objects.create(name="Test", external_id="123")
        self.room.contact = contact
        self.room.save()

        # Contact message doesn't set has_agent_messages
        Message.objects.create(room=self.room, contact=contact, text="Hi there")

        result = self.service.send_automatic_message(
            self.room, self.sector.automatic_message_text, self.user
        )

        self.assertTrue(result)

    def test_automatic_message_blocked_fallback_for_old_rooms(self, mock_ff):
        """
        Automatic message should NOT be sent for old rooms that have agent messages
        but has_agent_messages field is still False (not migrated).
        This tests the hybrid fallback behavior.
        """
        # Simulate old room: create agent message WITHOUT updating denormalized field
        Message.objects.create(room=self.room, user=self.user, text="Hello!")
        # Ensure has_agent_messages is False (simulating old room)
        self.assertFalse(self.room.has_agent_messages)

        result = self.service.send_automatic_message(
            self.room, self.sector.automatic_message_text, self.user
        )

        # Should still be blocked due to fallback query
        self.assertFalse(result)


@patch(
    "chats.apps.sectors.services.is_feature_active",
    return_value=False,
)
class TestAutomaticMessageWithFeatureFlagDisabled(TestCase):
    """
    Tests automatic message behavior when feature flag is disabled (legacy mode).
    Should use direct queries instead of denormalized fields.
    """

    def setUp(self):
        self.service = AutomaticMessagesService()
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
            is_automatic_message_active=True,
            automatic_message_text="Welcome!",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create(email="agent@test.com")
        self.room = Room.objects.create(queue=self.queue)

    def test_automatic_message_blocked_by_query_when_ff_disabled(self, mock_ff):
        """
        When feature flag is disabled, should use direct query to check agent messages.
        """
        # Create message without updating denormalized field
        Message.objects.create(room=self.room, user=self.user, text="Hello!")

        result = self.service.send_automatic_message(
            self.room, self.sector.automatic_message_text, self.user
        )

        # Should be blocked by direct query
        self.assertFalse(result)

    def test_automatic_message_allowed_when_no_messages_ff_disabled(self, mock_ff):
        """
        When feature flag is disabled and no agent messages, should allow.
        """
        result = self.service.send_automatic_message(
            self.room, self.sector.automatic_message_text, self.user
        )

        self.assertTrue(result)
