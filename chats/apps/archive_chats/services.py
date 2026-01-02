from abc import ABC, abstractmethod
import io
import json
import logging
import boto3
import requests

from typing import List
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from sentry_sdk import capture_exception


from chats.apps.archive_chats.choices import ArchiveConversationsJobStatus
from chats.apps.archive_chats.dataclass import ArchiveMessageMedia
from chats.apps.archive_chats.helpers import (
    generate_unique_filename,
    get_filename_from_url,
)
from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.apps.archive_chats.serializers import ArchiveMessageSerializer
from chats.apps.archive_chats.uploads import get_media_upload_to
from chats.apps.rooms.models import Room
from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.core.integrations.aws.s3.helpers import is_file_in_the_same_bucket


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
    def upload_media_file(self, message_media: MessageMedia) -> None:
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
                    original_filename = (
                        media.media_file.name
                        if media.media_file
                        else get_filename_from_url(media.media_url)
                    )

                    unique_filename = generate_unique_filename(
                        original_filename, used_media_filenames
                    )

                    key = self.upload_media_file(media, unique_filename)
                    used_media_filenames.add(unique_filename)

                    media_data.append(
                        ArchiveMessageMedia(url=key, content_type=media.content_type)
                    )

            messages_data.append(
                ArchiveMessageSerializer(message, context={"media": media_data}).data
            )

        return messages_data

    def upload_messages_file(
        self,
        room_archived_conversation: RoomArchivedConversation,
        messages: List[dict],
    ) -> None:
        """
        Upload a messages file to the archived conversations location.
        """
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

        return room_archived_conversation

    def upload_media_file(self, message_media: MessageMedia, filename: str) -> str:
        """
        Upload a media file to the archived conversations location.
        """
        if message_media.media_file:
            url = message_media.media_file.url
            same_bucket = is_file_in_the_same_bucket(url, self.bucket.name)
        else:
            url = message_media.media_url
            same_bucket = False

        if same_bucket:
            key = self._copy_file_using_server_side_copy(message_media, filename)
        else:
            key = self._copy_file_using_client_side_copy(message_media, filename)

        return key

    def _copy_file_using_server_side_copy(
        self, message_media: MessageMedia, filename: str
    ) -> str:
        """
        Copy a file from the original bucket to the new bucket using server-side copy.
        """
        original_key = message_media.media_file.name
        new_key = get_media_upload_to(message_media.message, filename)

        self.bucket.copy(
            {
                "Bucket": self.bucket.name,
                "Key": original_key,
            },
            new_key,
        )

        return new_key

    def _copy_file_using_client_side_copy(
        self, message_media: MessageMedia, filename: str
    ) -> str:
        """
        Copy a file from the original url to the target bucket using client-side copy.
        """
        original_url = message_media.media_url
        new_key = get_media_upload_to(message_media.message, filename)

        with requests.get(original_url, stream=True, timeout=60) as response:
            response.raise_for_status()

            self.bucket.upload_fileobj(response.raw, new_key)

        return new_key
