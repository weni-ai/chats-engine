from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.apps.archive_chats.services import ArchiveChatsService
from chats.apps.rooms.models import Room
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector
from chats.apps.projects.models import Project


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
