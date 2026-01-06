from abc import ABC, abstractmethod
import io
import json
import logging

from typing import List
from django.utils import timezone
from django.core.files.base import ContentFile
from sentry_sdk import capture_exception


from chats.apps.archive_chats.choices import ArchiveConversationsJobStatus
from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.apps.archive_chats.serializers import ArchiveMessageSerializer
from chats.apps.rooms.models import Room
from chats.apps.msgs.models import (
    Message,
)


logger = logging.getLogger(__name__)


class BaseArchiveChatsService(ABC):
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
    def delete_room_messages(self, room: Room) -> None:
        pass


class ArchiveChatsService(BaseArchiveChatsService):
    def start_archive_job(self) -> ArchiveConversationsJob:
        logger.info("[ArchiveChatsService] Starting archive job")

        return ArchiveConversationsJob.objects.create(
            started_at=timezone.now(),
        )

    def archive_room_history(self, room: Room, job: ArchiveConversationsJob) -> None:
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

        for message in messages:
            if message.medias.exists():
                for media in message.medias.all():  # noqa
                    # TODO: Implement media processing
                    pass

            messages_data.append(ArchiveMessageSerializer(message).data)

        return messages_data

    def upload_messages_file(
        self,
        room_archived_conversation: RoomArchivedConversation,
        messages: List[dict],
    ) -> None:
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

    def delete_room_messages(self, room: Room, batch_size: int = 1000) -> None:
        logger.info(
            f"[ArchiveChatsService] Deleting room messages for room {room.uuid}"
        )

        messages = Message.objects.filter(room=room)

        for i in range(0, len(messages), batch_size):
            messages_batch = messages[i : i + batch_size]

            if not messages_batch.exists():
                break

            messages_batch.delete()

        logger.info(f"[ArchiveChatsService] Room messages deleted for room {room.uuid}")
