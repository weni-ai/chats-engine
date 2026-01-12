from abc import ABC, abstractmethod
import io
import json
import logging
import boto3

import re
from typing import List
from django.conf import settings
from uuid import UUID
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.files.base import ContentFile
from sentry_sdk import capture_exception


from chats.apps.archive_chats.choices import ArchiveConversationsJobStatus
from chats.apps.archive_chats.exceptions import InvalidObjectKey
from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.apps.archive_chats.serializers import ArchiveMessageSerializer
from chats.apps.core.integrations.aws.s3.helpers import get_presigned_url
from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.rooms.models import Room


logger = logging.getLogger(__name__)


class BaseArchiveChatsService(ABC):
    """
    Base class for archive chats services.
    """

    @abstractmethod
    def archive_room_history(self, room: Room, job: ArchiveConversationsJob) -> None:
        pass

    @abstractmethod
    def process_messages(
        self, room_archived_conversation: RoomArchivedConversation
    ) -> List[ArchiveMessageSerializer]:
        pass

    @abstractmethod
    def upload_messages_file(self, messages: List[dict]) -> None:
        pass

    @abstractmethod
    def get_archived_media_url(self, object_key: str) -> str:
        pass


class ArchiveChatsService(BaseArchiveChatsService):
    """
    Service to archive the history of a room.
    """

    def __init__(self, bucket=None):
        self.bucket = bucket or boto3.resource("s3").Bucket(
            settings.AWS_STORAGE_BUCKET_NAME
        )

    def start_archive_job(self) -> ArchiveConversationsJob:
        """
        Start a new archive job.
        """
        logger.info("[ArchiveChatsService] Starting archive job")

        return ArchiveConversationsJob.objects.create(
            started_at=timezone.now(),
        )

    def archive_room_history(self, room: Room, job: ArchiveConversationsJob) -> None:
        """
        Archive the history of a room.
        """
        logger.info(
            f"[ArchiveChatsService] Archiving room history for room {room.uuid} with job {job.uuid}"
        )

        room_archived_conversation = RoomArchivedConversation.objects.create(
            job=job,
            room=room,
            status=ArchiveConversationsJobStatus.PENDING,
        )
        logger.info(
            f"[ArchiveChatsService] Room archived conversation created: "
            f"{room_archived_conversation.uuid} with status "
            f"{room_archived_conversation.status} for room {room.uuid} "
            f"and job {job.uuid}"
        )

        try:
            messages_data = self.process_messages(room_archived_conversation)
            self.upload_messages_file(room_archived_conversation, messages_data)

            room_archived_conversation.refresh_from_db()
            room_archived_conversation.status = ArchiveConversationsJobStatus.FINISHED
            room_archived_conversation.archive_process_finished_at = timezone.now()
            room_archived_conversation.save(
                update_fields=["status", "archive_process_finished_at"]
            )
        except Exception as e:
            sentry_event_id = capture_exception(e)
            room_archived_conversation.register_error(e, sentry_event_id)
            logger.error(
                f"[ArchiveChatsService] Error archiving room history for room {room.uuid} with job {job.uuid}: {e}",
                exc_info=True,
            )

        room_archived_conversation.refresh_from_db()

        return room_archived_conversation

    def process_messages(
        self, room_archived_conversation: RoomArchivedConversation
    ) -> List[ArchiveMessageSerializer]:
        """
        Process the messages of a room and return the messages data.
        """
        room = room_archived_conversation.room

        room_archived_conversation.status = (
            ArchiveConversationsJobStatus.PROCESSING_MESSAGES
        )
        room_archived_conversation.archive_process_started_at = timezone.now()
        room_archived_conversation.save(
            update_fields=["status", "archive_process_started_at"]
        )

        logger.info(
            f"[ArchiveChatsService] Room archived conversation status updated to "
            f"{room_archived_conversation.status} for room {room.uuid} "
            f"with archived conversation {room_archived_conversation.uuid}"
        )

        messages_data: List[ArchiveMessageSerializer] = []
        messages = Message.objects.filter(room=room).order_by("created_on")

        used_media_filenames = set()

        for message in messages:
            media_data = []
            if message.medias.exists():
                for media in message.medias.all():  # noqa
                    # TODO
                    pass

            messages_data.append(
                ArchiveMessageSerializer(message, context={"media": media_data}).data
            )

        room_archived_conversation.status = (
            ArchiveConversationsJobStatus.MESSAGES_PROCESSED
        )
        room_archived_conversation.save(update_fields=["status"])

        return messages_data

    def upload_messages_file(
        self,
        room_archived_conversation: RoomArchivedConversation,
        messages: List[dict],
    ) -> None:
        """
        Upload a messages file to the archived conversations location.
        """

        if (
            room_archived_conversation.status
            != ArchiveConversationsJobStatus.MESSAGES_PROCESSED
        ):
            raise ValidationError(
                f"Room archived conversation {room_archived_conversation.uuid} is not in messages processed status"
            )

        room_archived_conversation.status = (
            ArchiveConversationsJobStatus.UPLOADING_MESSAGES_FILE
        )
        room_archived_conversation.save(update_fields=["status"])

        logger.info(
            f"[ArchiveChatsService] Room archived conversation status updated to "
            f"{room_archived_conversation.status} for room {room_archived_conversation.room.uuid} "
            f"with archived conversation {room_archived_conversation.uuid}"
        )

        file_object = io.BytesIO()

        for message in messages:
            file_object.write(json.dumps(message).encode("utf-8"))
            file_object.write(b"\n")

        file_object.seek(0)

        filename = "messages.jsonl"

        room_archived_conversation.file.save(
            filename,
            ContentFile(file_object.read()),
            save=True,
        )

        room_archived_conversation.status = (
            ArchiveConversationsJobStatus.MESSAGES_FILE_UPLOADED
        )
        room_archived_conversation.save(update_fields=["status"])

        return room_archived_conversation

    def get_archived_media_url(self, object_key: str) -> str:
        valid_pattern = r"^archived_conversations/[^/]+/[^/]+/media/[^/]+$"

        if not re.fullmatch(valid_pattern, object_key):
            raise InvalidObjectKey("Invalid object key")

        parts = object_key.split("/")

        project_uuid = parts[1]
        room_uuid = parts[2]

        for _uuid in (project_uuid, room_uuid):
            try:
                UUID(_uuid)
            except ValueError:
                raise InvalidObjectKey("Invalid object key")

        return get_presigned_url(object_key)
