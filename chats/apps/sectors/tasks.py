from uuid import UUID
from chats.apps.rooms.models import Room
from chats.apps.sectors.services import AutomaticMessagesService
from chats.apps.accounts.models import User


from chats.celery import app


@app.task
def send_automatic_message(room_uuid: UUID, message: str, user: User):
    """
    Send an automatic message to a room.
    """
    room = Room.objects.get(uuid=room_uuid)

    AutomaticMessagesService().send_automatic_message(room, message, user)
