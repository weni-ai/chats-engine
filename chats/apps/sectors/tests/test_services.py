from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import AutomaticMessage, Message
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.sectors.services import AutomaticMessagesService


class TestAutomaticMessagesService(TestCase):
    def setUp(self):
        self.service = AutomaticMessagesService()
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(queue=self.queue)
        self.user = User.objects.create(email="test@test.com")

    def test_send_automatic_message_when_sector_automatic_message_is_not_active(self):
        self.assertFalse(
            self.service.send_automatic_message(
                self.room, self.sector.automatic_message_text, self.user
            )
        )

    def test_send_automatic_message_when_sector_automatic_message_text_is_not_set(self):
        self.sector.is_automatic_message_active = True
        self.sector.automatic_message_text = ""
        self.sector.save()
        self.assertFalse(
            self.service.send_automatic_message(
                self.room, self.sector.automatic_message_text, self.user
            )
        )

    def test_send_automatic_message_when_room_already_has_automatic_message(self):
        AutomaticMessage.objects.create(
            room=self.room,
            message=Message.objects.create(
                room=self.room,
                text=self.sector.automatic_message_text,
                user=self.user,
                contact=None,
            ),
        )
        self.assertFalse(
            self.service.send_automatic_message(
                self.room, self.sector.automatic_message_text, self.user
            )
        )

    def test_send_automatic_message_when_room_already_has_messages(self):
        Message.objects.create(
            room=self.room,
            text=self.sector.automatic_message_text,
            user=self.user,
            contact=None,
        )
        self.assertFalse(
            self.service.send_automatic_message(
                self.room, self.sector.automatic_message_text, self.user
            )
        )

    def test_send_automatic_message_when_all_conditions_are_met(self):
        self.sector.is_automatic_message_active = True
        self.sector.automatic_message_text = "Test Message"
        self.sector.save()
        self.assertTrue(
            self.service.send_automatic_message(
                self.room, self.sector.automatic_message_text, self.user
            )
        )


class TestHasAgentMessages(TestCase):
    """Tests for has_agent_messages denormalized field and fallback"""

    def setUp(self):
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
        self.service = AutomaticMessagesService()

    def test_get_has_agent_messages_returns_false_when_no_messages(self):
        self.assertFalse(self.room.get_has_agent_messages())

    def test_get_has_agent_messages_returns_true_when_field_is_set(self):
        Room.objects.filter(pk=self.room.pk).update(has_agent_messages=True)
        self.room.refresh_from_db()
        self.assertTrue(self.room.get_has_agent_messages())

    def test_get_has_agent_messages_fallback_when_field_is_false(self):
        """Old rooms with agent messages but has_agent_messages=False should fallback to query"""
        Message.objects.create(room=self.room, user=self.user, text="Hello!")
        self.assertFalse(self.room.has_agent_messages)
        self.assertTrue(self.room.get_has_agent_messages())

    def test_get_has_agent_messages_false_with_only_contact_messages(self):
        contact = Contact.objects.create(name="Test", external_id="123")
        Message.objects.create(room=self.room, contact=contact, text="Hi")
        self.assertFalse(self.room.get_has_agent_messages())

    def test_update_last_message_sets_has_agent_messages(self):
        msg = Message.objects.create(room=self.room, user=self.user, text="Hello")
        self.room.update_last_message(message=msg, user=self.user)
        self.room.refresh_from_db()
        self.assertTrue(self.room.has_agent_messages)

    def test_update_last_message_without_user_does_not_set_has_agent_messages(self):
        msg = Message.objects.create(room=self.room, text="System message")
        self.room.update_last_message(message=msg, user=None)
        self.room.refresh_from_db()
        self.assertFalse(self.room.has_agent_messages)

    def test_automatic_message_blocked_when_agent_message_exists_via_field(self):
        """Automatic message should NOT be sent when has_agent_messages is True"""
        Room.objects.filter(pk=self.room.pk).update(has_agent_messages=True)
        self.room.refresh_from_db()
        result = self.service.send_automatic_message(
            self.room, self.sector.automatic_message_text, self.user
        )
        self.assertFalse(result)

    def test_automatic_message_blocked_by_fallback_for_old_rooms(self):
        """Old rooms without denormalized field should still block via query fallback"""
        Message.objects.create(room=self.room, user=self.user, text="Hello!")
        self.assertFalse(self.room.has_agent_messages)
        result = self.service.send_automatic_message(
            self.room, self.sector.automatic_message_text, self.user
        )
        self.assertFalse(result)

    def test_automatic_message_allowed_when_no_agent_messages(self):
        result = self.service.send_automatic_message(
            self.room, self.sector.automatic_message_text, self.user
        )
        self.assertTrue(result)

    def test_automatic_message_allowed_with_only_contact_messages(self):
        contact = Contact.objects.create(name="Test", external_id="123")
        self.room.contact = contact
        self.room.save()
        Message.objects.create(room=self.room, contact=contact, text="Hi there")
        result = self.service.send_automatic_message(
            self.room, self.sector.automatic_message_text, self.user
        )
        self.assertTrue(result)
