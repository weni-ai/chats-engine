import json
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.apps.archive_chats.serializers import ArchiveMessageSerializer
from chats.apps.archive_chats.services import ArchiveChatsService
from chats.apps.msgs.models import Message
from chats.apps.rooms.models import Room
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector
from chats.apps.projects.models import Project
from chats.apps.contacts.models import Contact
from chats.apps.accounts.models import User


class TestArchiveChatsService(TestCase):
    def setUp(self):
        self.service = ArchiveChatsService()
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(sector=self.sector)
        self.room = Room.objects.create(queue=self.queue)
        self.user = User.objects.create(
            email="test@example.com", first_name="Test", last_name="User"
        )
        self.contact = Contact.objects.create(name="Test Contact")

    def test_start_archive_job(self):
        self.assertFalse(ArchiveConversationsJob.objects.exists())

        now = timezone.now()

        with patch("chats.apps.archive_chats.services.timezone.now") as mock_now:
            mock_now.return_value = now
            job = self.service.start_archive_job()

        self.assertIsNotNone(job)
        self.assertEqual(job.started_at, now)

    @patch("chats.apps.archive_chats.services.ArchiveChatsService.process_messages")
    def test_archive_room_history(self, mock_process_messages):
        mock_process_messages.return_value = []
        self.assertFalse(RoomArchivedConversation.objects.exists())

        job = self.service.start_archive_job()

        self.service.archive_room_history(self.room, job)

        archived_conversation = RoomArchivedConversation.objects.first()
        self.assertIsNotNone(archived_conversation)

        self.assertEqual(archived_conversation.room, self.room)
        self.assertEqual(archived_conversation.job, job)

        mock_process_messages.assert_called_once_with(archived_conversation)

    def test_process_messages(self):
        message_a = Message.objects.create(
            room=self.room,
            user=self.user,
            text="Test message",
            created_on=timezone.now(),
        )
        message_b = Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="Test message",
            created_on=timezone.now(),
        )
        messages = [message_a, message_b]

        archived_conversation = RoomArchivedConversation.objects.create(
            job=self.service.start_archive_job(),
            room=self.room,
            file="test.zip",
            archive_process_started_at=timezone.now(),
            archive_process_finished_at=timezone.now(),
            messages_deleted_at=timezone.now(),
        )
        messages_data = self.service.process_messages(archived_conversation)

        self.assertIsInstance(messages_data, list)
        self.assertEqual(len(messages_data), 2)

        for i, message in enumerate(messages):
            self.assertEqual(messages_data[i].get("uuid"), str(message.uuid))
            self.assertEqual(messages_data[i].get("text"), message.text)
            self.assertEqual(
                messages_data[i].get("created_on"), message.created_on.isoformat()
            )
            user_data = messages_data[i].get("user", {}) or {}
            self.assertEqual(
                user_data.get("email"),
                message.user.email if message.user else None,
            )
            contact_data = messages_data[i].get("contact", {}) or {}
            self.assertEqual(
                contact_data.get("external_id"),
                message.contact.external_id if message.contact else None,
            )
            self.assertEqual(
                contact_data.get("name"),
                message.contact.name if message.contact else None,
            )

    def test_upload_messages_file(self):
        archived_conversation = RoomArchivedConversation.objects.create(
            job=self.service.start_archive_job(),
            room=self.room,
        )

        message_a = Message.objects.create(
            room=self.room,
            user=self.user,
            text="Test message",
            created_on=timezone.now(),
        )
        message_b = Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="Test message",
            created_on=timezone.now(),
        )

        messages = [
            ArchiveMessageSerializer(message_a).data,
            ArchiveMessageSerializer(message_b).data,
        ]

        self.service.upload_messages_file(
            room_archived_conversation=archived_conversation,
            messages=messages,
        )

        archived_conversation.refresh_from_db()

        self.assertTrue(archived_conversation.file)
        self.assertEqual(
            archived_conversation.file.name,
            f"archived_conversations/{self.project.uuid}/{self.room.uuid}/messages.jsonl",
        )

        with archived_conversation.file.open("r") as f:
            lines = f.read().splitlines()

        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0]), messages[0])
        self.assertEqual(json.loads(lines[1]), messages[1])
