from uuid import UUID

from django.db.models import QuerySet

from chats.apps.msgs.exceptions import RoomNotFoundError, RoomStillActiveError
from chats.apps.msgs.models import Message
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room


class GetRoomMessagesHistoryUseCase:
    """
    Returns the message history queryset for a closed room that belongs to the
    given project.

    Raises ``RoomNotFoundError`` when the room does not exist or does not
    belong to the project.  Raises ``RoomStillActiveError`` when the room
    has not been closed yet.

    Internal notes are excluded at the database level by filtering on the
    reverse ``internal_note`` OneToOne relation declared on
    ``RoomNote.message``.
    """

    def execute(self, room_uuid: UUID, project: Project) -> "QuerySet[Message]":
        room = (
            Room.objects.filter(
                uuid=room_uuid,
                queue__sector__project=project,
            )
            .only("uuid", "is_active")
            .first()
        )
        if room is None:
            raise RoomNotFoundError()

        if room.is_active:
            raise RoomStillActiveError()

        return (
            Message.objects.filter(room=room, internal_note__isnull=True)
            .select_related("user", "contact")
            .prefetch_related("medias")
            .order_by("-created_on")
        )
