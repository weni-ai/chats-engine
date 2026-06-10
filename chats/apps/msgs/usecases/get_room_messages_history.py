from django.db.models import QuerySet

from chats.apps.msgs.models import Message
from chats.apps.rooms.models import Room


class GetRoomMessagesHistoryUseCase:
    """
    Builds the queryset of messages that compose the history of a room.

    Internal notes are excluded at the database level (not on the application
    side) by filtering on the reverse ``internal_note`` OneToOne relation
    declared on ``RoomNote.message``.
    """

    def execute(self, room: Room) -> "QuerySet[Message]":
        return (
            Message.objects.filter(room=room, internal_note__isnull=True)
            .select_related("user", "contact")
            .prefetch_related("medias")
            .order_by("-created_on")
        )
