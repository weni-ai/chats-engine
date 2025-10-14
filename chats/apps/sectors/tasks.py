from uuid import UUID
from chats.apps.sectors.services import AutomaticMessagesService
from chats.apps.accounts.models import User


from chats.celery import app


@app.task
def send_automatic_message(
    room_uuid: UUID, message: str, user_id: int, check_ticket: bool = False
):
    """
    Send an automatic message to a room.
    """
    from chats.apps.rooms.models import Room

    room = Room.objects.get(uuid=room_uuid)
    user = User.objects.get(id=user_id)

    AutomaticMessagesService().send_automatic_message(room, message, user, check_ticket)
