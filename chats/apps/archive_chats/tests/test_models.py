from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from django.utils import timezone
from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room


class TestArchiveConversationsJob(TestCase):
    def test_str(self):
        job = ArchiveConversationsJob.objects.create(started_at=timezone.now())
        self.assertEqual(
            str(job), f"Archive Conversations Job {job.uuid} - {job.started_at}"
        )


class TestRoomArchivedConversation(TestCase):
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
        self.room = Room.objects.create(queue=self.queue)
        self.job = ArchiveConversationsJob.objects.create(started_at=timezone.now())

    def test_str(self):
        conversation = RoomArchivedConversation.objects.create(
            job=self.job,
            room=self.room,
            file="test.zip",
            archive_process_started_at=timezone.now(),
            archive_process_finished_at=timezone.now(),
            messages_deleted_at=timezone.now(),
        )
        self.assertEqual(
            str(conversation),
            f"Room Archived Conversation {conversation.room.uuid} - {conversation.room.queue.sector.project.name}",
        )

    def test_register_error(self):
        conversation = RoomArchivedConversation.objects.create(
            job=self.job,
            room=self.room,
            file="test.zip",
            archive_process_started_at=timezone.now(),
            archive_process_finished_at=timezone.now(),
            messages_deleted_at=timezone.now(),
        )
        conversation.register_error(Exception("Test error"))

        self.assertEqual(len(conversation.errors), 1)
        self.assertEqual(conversation.errors[0]["error"], "Test error")
        self.assertIsNotNone(conversation.errors[0]["traceback"])
        self.assertIsNone(conversation.errors[0]["sentry_event_id"])

        try:
            1 / 0
        except Exception as e:
            conversation.register_error(e, sentry_event_id="test-event-id")

        self.assertEqual(len(conversation.errors), 2)
        self.assertEqual(conversation.errors[1]["error"], "division by zero")
        self.assertIsNotNone(conversation.errors[1]["traceback"])
        self.assertEqual(conversation.errors[1]["sentry_event_id"], "test-event-id")

    def test_file_upload_to(self):
        test_file = SimpleUploadedFile(
            "test.jsonl", b"fake jsonl content", content_type="application/jsonl"
        )

        conversation = RoomArchivedConversation.objects.create(
            job=self.job,
            room=self.room,
            file=test_file,
            archive_process_started_at=timezone.now(),
            archive_process_finished_at=timezone.now(),
            messages_deleted_at=timezone.now(),
        )

        project_uuid = self.room.queue.sector.project.uuid
        room_uuid = self.room.uuid

        expected_path = f"archived_conversations/{project_uuid}/{room_uuid}/test.jsonl"
        self.assertEqual(conversation.file.name, expected_path)
