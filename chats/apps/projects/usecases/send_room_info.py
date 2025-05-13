from typing import TYPE_CHECKING
from chats.apps.api.v1.internal.eda_clients.billing_client import RoomsInfoMixin


if TYPE_CHECKING:
    from chats.apps.rooms.models import Room


class RoomInfoUseCase:
    def __init__(self):
        self._rooms_client = RoomsInfoMixin()

    def get_room(self, room: Room):
        room = {
            "uuid": str(room.uuid),
            "project_uuid": str(room.project.uuid),
            "external_id": room.contact.external_id,
            "created_on": room.created_on.isoformat(),
        }
        self._rooms_client.request_room(content=room)
