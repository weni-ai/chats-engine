import json
from unittest.mock import patch
import uuid

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from chats.apps.archive_chats.choices import ArchiveConversationsJobStatus
from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.apps.archive_chats.serializers import ArchiveMessageSerializer
from chats.apps.archive_chats.services import ArchiveChatsService
from chats.apps.msgs.models import AutomaticMessage, Message, MessageMedia
from chats.apps.rooms.models import Room, RoomNote
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector
from chats.apps.projects.models import Project
from chats.apps.contacts.models import Contact
from chats.apps.accounts.models import User
from chats.apps.archive_chats.exceptions import InvalidObjectKey


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

    @patch("chats.apps.archive_chats.services.ArchiveChatsService.process_messages")
    @patch("chats.apps.archive_chats.services.capture_exception")
    def test_archive_room_history_with_error(
        self, mock_capture_exception, mock_process_messages
    ):
        mock_capture_exception.return_value = "test-event-id"
        mock_process_messages.side_effect = Exception("Test error")
        self.assertFalse(RoomArchivedConversation.objects.exists())

        now = timezone.now()

        with patch(
            "chats.apps.archive_chats.services.timezone.now"
        ) as mock_service_now, patch(
            "chats.apps.archive_chats.models.timezone.now"
        ) as mock_model_now:
            mock_service_now.return_value = now
            mock_model_now.return_value = now
            job = self.service.start_archive_job()
            self.service.archive_room_history(self.room, job)

        archived_conversation = RoomArchivedConversation.objects.first()

        self.assertEqual(
            archived_conversation.status, ArchiveConversationsJobStatus.FAILED
        )
        self.assertEqual(archived_conversation.failed_at, now)
        self.assertEqual(len(archived_conversation.errors), 1)
        self.assertEqual(archived_conversation.errors[0]["error"], "Test error")
        self.assertIsNotNone(archived_conversation.errors[0]["traceback"])
        self.assertEqual(
            archived_conversation.errors[0]["sentry_event_id"], "test-event-id"
        )

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
        message_c = Message.objects.create(
            room=self.room,
            user=self.user,
            text="Test message",
            created_on=timezone.now(),
        )
        AutomaticMessage.objects.create(
            message=message_c,
            room=self.room,
        )
        message_d = Message.objects.create(
            room=self.room,
            user=self.user,
            text="Test message",
            created_on=timezone.now(),
        )
        RoomNote.objects.create(
            room=self.room,
            user=self.user,
            text="Test note",
        )
        messages = [message_a, message_b, message_c, message_d]

        archived_conversation = RoomArchivedConversation.objects.create(
            job=self.service.start_archive_job(),
            room=self.room,
            file="test.zip",
            archive_process_started_at=timezone.now(),
            archive_process_finished_at=timezone.now(),
            messages_deleted_at=timezone.now(),
        )
        messages_data = self.service.process_messages(archived_conversation)

        archived_conversation.refresh_from_db()
        self.assertEqual(
            archived_conversation.status,
            ArchiveConversationsJobStatus.MESSAGES_PROCESSED,
        )
        self.assertIsNotNone(archived_conversation.archive_process_started_at)

        self.assertIsInstance(messages_data, list)
        self.assertEqual(len(messages_data), 4)

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
            self.assertEqual(
                messages_data[i].get("is_automatic_message"),
                message.is_automatic_message,
            )

            if internal_note := getattr(message, "internal_note", None):
                self.assertEqual(
                    messages_data[i].get("internal_note"),
                    {
                        "uuid": str(internal_note.uuid),
                        "text": internal_note.text,
                    },
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

        archived_conversation.status = ArchiveConversationsJobStatus.MESSAGES_PROCESSED
        archived_conversation.save(update_fields=["status"])

        self.service.upload_messages_file(
            room_archived_conversation=archived_conversation,
            messages=messages,
        )

        archived_conversation.refresh_from_db()

        self.assertEqual(
            archived_conversation.status,
            ArchiveConversationsJobStatus.MESSAGES_FILE_UPLOADED,
        )
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

    def test_upload_messages_file_when_status_is_not_messages_processed(self):
        archived_conversation = RoomArchivedConversation.objects.create(
            job=self.service.start_archive_job(),
            room=self.room,
            status=ArchiveConversationsJobStatus.PENDING,
        )

        with self.assertRaises(ValidationError) as context:
            self.service.upload_messages_file(
                room_archived_conversation=archived_conversation,
                messages=[],
            )

        self.assertEqual(
            context.exception.message,
            f"Room archived conversation {archived_conversation.uuid} is not in messages processed status",
        )

        archived_conversation.refresh_from_db()

        self.assertEqual(
            archived_conversation.status,
            ArchiveConversationsJobStatus.PENDING,
        )

    @patch("chats.apps.archive_chats.services.get_presigned_url")
    def test_get_archived_media_url(self, mock_get_presigned_url):
        object_key = f"archived_conversations/{self.project.uuid}/{self.room.uuid}/media/test.jpg"
        mock_get_presigned_url.return_value = (
            f"https://test-bucket.s3.amazonaws.com/{object_key}"
        )

        RoomArchivedConversation.objects.create(
            job=self.service.start_archive_job(),
            room=self.room,
            status=ArchiveConversationsJobStatus.FINISHED,
        )

        url = self.service.get_archived_media_url(object_key)

        self.assertEqual(
            url,
            f"https://test-bucket.s3.amazonaws.com/{object_key}",
        )

    def test_get_archived_media_url_with_invalid_project_uuid(self):
        valid_uuid = uuid.uuid4()
        with self.assertRaises(InvalidObjectKey):
            self.service.get_archived_media_url(
                f"archived_conversations/invalid-project-uuid/{valid_uuid}/media/test.jpg"
            )

    def test_get_archived_media_url_with_invalid_room_uuid(self):
        valid_uuid = uuid.uuid4()
        with self.assertRaises(InvalidObjectKey):
            self.service.get_archived_media_url(
                f"archived_conversations/{valid_uuid}/invalid-room-uuid/media/test.jpg"
            )

    def test_get_archived_media_url_without_media_part(self):
        valid_uuid = uuid.uuid4()
        with self.assertRaises(InvalidObjectKey):
            self.service.get_archived_media_url(
                f"archived_conversations/{valid_uuid}/{valid_uuid}/messages.jsonl"
            )

    def test_get_archived_media_url_with_room_not_archived(self):
        with self.assertRaises(InvalidObjectKey):
            self.service.get_archived_media_url(
                f"archived_conversations/{self.project.uuid}/{self.room.uuid}/media/test.jpg"
            )

    def test_get_archived_media_url_with_non_existent_room(self):
        with self.assertRaises(InvalidObjectKey):
            self.service.get_archived_media_url(
                f"archived_conversations/{self.project.uuid}/{uuid.uuid4()}/media/test.jpg"
            )

    def test_delete_room_messages(self):
        archived_conversation = RoomArchivedConversation.objects.create(
            job=self.service.start_archive_job(),
            room=self.room,
            status=ArchiveConversationsJobStatus.MESSAGES_FILE_UPLOADED,
        )

        messages = [
            Message.objects.create(
                room=self.room,
                user=self.user,
                text="Test message",
                created_on=timezone.now(),
            ),
            Message.objects.create(
                room=self.room,
                contact=self.contact,
                text="Test message",
                created_on=timezone.now(),
            ),
            Message.objects.create(
                room=self.room,
                contact=self.contact,
                text="Test message",
                created_on=timezone.now(),
            ),
        ]

        MessageMedia.objects.create(
            message=messages[0],
            content_type="image/png",
            media_file="test.png",
        )
        AutomaticMessage.objects.create(
            message=messages[0],
            room=self.room,
        )

        self.service.delete_room_messages(archived_conversation, batch_size=2)

        archived_conversation.refresh_from_db()
        self.assertEqual(
            archived_conversation.status,
            ArchiveConversationsJobStatus.MESSAGES_DELETED_FROM_DB,
        )

        self.assertEqual(Message.objects.filter(room=self.room).count(), 0)
        self.assertEqual(
            MessageMedia.objects.filter(message__room=self.room).count(), 0
        )
        self.assertEqual(
            AutomaticMessage.objects.filter(message__room=self.room).count(), 0
        )
