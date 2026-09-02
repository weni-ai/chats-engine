from django.db import transaction

from chats.apps.msgs.models import Message
from chats.apps.rooms.models import RoomNote


class CreateRoomNoteUseCase:
    def execute(self, room, user, text: str) -> RoomNote:
        with transaction.atomic():
            msg = Message.objects.create(
                room=room, user=user, contact=None, text=""
            )
            note = RoomNote.objects.create(
                room=room, user=user, text=text, message=msg
            )
            transaction.on_commit(lambda: msg.notify_room("create", True))
        return note
