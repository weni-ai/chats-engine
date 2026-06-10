from django.test import TestCase


from chats.apps.sectors.services import AutomaticMessagesService
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project
from chats.apps.msgs.models import Message, AutomaticMessage


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
