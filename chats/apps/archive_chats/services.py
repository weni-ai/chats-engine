from abc import ABC, abstractmethod
import logging


from django.utils import timezone


from chats.apps.archive_chats.choices import ArchiveConversationsJobStatus
from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.apps.archive_chats.serializers import ArchiveMessageSerializer
from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.rooms.models import Room


logger = logging.getLogger(__name__)


class BaseArchiveChatsService(ABC):
    @abstractmethod
    def archive_room_history(self, room: Room, job: ArchiveConversationsJob) -> None:
        pass

    @abstractmethod
    def process_messages(
        self, room_archived_conversation: RoomArchivedConversation
    ) -> list[ArchiveMessageSerializer]:
        pass

    @abstractmethod
    def upload_messages_file(self, messages: list[ArchiveMessageSerializer]) -> None:
        pass

    @abstractmethod
    def process_media_message(self, message_media: MessageMedia) -> None:
        pass

    @abstractmethod
    def upload_media_file(self, message_media: MessageMedia) -> str:
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

        messages_data = self.process_messages(room_archived_conversation)  # noqa

    def process_messages(
        self, room_archived_conversation: RoomArchivedConversation
    ) -> list[ArchiveMessageSerializer]:
        room = room_archived_conversation.room

        room_archived_conversation.status = (
            ArchiveConversationsJobStatus.PROCESSING_MESSAGES
        )
        room_archived_conversation.save(update_fields=["status"])

        messages_data: list[ArchiveMessageSerializer] = []
        messages = Message.objects.filter(room=room).order_by("created_on")

        for message in messages:
            if message.media.exists():
                for media in message.media.all():
                    self.process_media_message(media)

            messages_data.append(ArchiveMessageSerializer(message).data)

        return messages_data

    def upload_messages_file(self, messages: list[ArchiveMessageSerializer]) -> None:
        pass

    def process_media_message(self, message_media: MessageMedia) -> None:
        # TODO: Implement this
        pass

    def upload_media_file(self, message_media: MessageMedia) -> str:
        # TODO: Implement this
        pass
