from abc import ABC, abstractmethod


from chats.apps.archive_chats.serializers import ArchiveMessageSerializer
from chats.apps.msgs.models import MessageMedia
from chats.apps.rooms.models import Room


class BaseArchiveChatsService(ABC):
    @abstractmethod
    def archive_room_history(self, room: Room) -> None:
        pass

    @abstractmethod
    def process_messages(self, room: Room) -> list[ArchiveMessageSerializer]:
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
    def archive_room_history(self, room: Room) -> None:
        pass

    def process_messages(self, room: Room) -> list[ArchiveMessageSerializer]:
        pass

    def upload_messages_file(self, messages: list[ArchiveMessageSerializer]) -> None:
        pass

    def process_media_message(self, message_media: MessageMedia) -> None:
        # TODO: Implement this
        pass

    def upload_media_file(self, message_media: MessageMedia) -> str:
        # TODO: Implement this
        pass
