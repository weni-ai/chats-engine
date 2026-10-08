from datetime import time
from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room, RoomNote
from chats.apps.rooms.usecases.create_room_note import CreateRoomNoteUseCase
from chats.apps.sectors.models import Sector


class CreateRoomNoteUseCaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="agent@example.com",
            password="testpass123",
            first_name="Maria",
            last_name="Silva",
        )
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(9, 0),
            work_end=time(18, 0),
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            name="Contact", email="contact@example.com"
        )
        self.room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        self.use_case = CreateRoomNoteUseCase()

    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_execute_creates_blank_message_and_note(self, mock_notify_room):
        note = self.use_case.execute(self.room, self.user, "Internal note text")

        self.assertEqual(note.text, "Internal note text")
        self.assertEqual(note.room, self.room)
        self.assertEqual(note.user, self.user)

        message = note.message
        self.assertIsNotNone(message)
        self.assertEqual(message.text, "")
        self.assertEqual(message.user, self.user)
        self.assertIsNone(message.contact)
        self.assertEqual(message.room, self.room)

    @patch("django.db.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_execute_notifies_room_on_commit(self, mock_notify_room, _mock_on_commit):
        self.use_case.execute(self.room, self.user, "Internal note text")

        mock_notify_room.assert_called_once_with("create", True)

    @patch(
        "chats.apps.rooms.usecases.create_room_note.RoomNote.objects.create",
        side_effect=RuntimeError("note create failed"),
    )
    def test_execute_rolls_back_message_when_note_create_fails(self, _mock_create):
        with self.assertRaises(RuntimeError):
            self.use_case.execute(self.room, self.user, "Internal note text")

        self.assertEqual(Message.objects.filter(room=self.room).count(), 0)
        self.assertEqual(RoomNote.objects.filter(room=self.room).count(), 0)
