from typing import TYPE_CHECKING
from django.conf import settings
from chats.apps.api.v1.internal.eda_clients.billing_client import RoomsInfoMixin


if TYPE_CHECKING:
    from chats.apps.rooms.models import Room


class RoomInfoUseCase:
    def __init__(self):
        self._rooms_client = RoomsInfoMixin()

    def get_room(self, room: "Room"):
        project_uuid = self._get_project_uuid(room)
        
        room_data = {
            "uuid": str(room.uuid),
            "project_uuid": project_uuid,
            "external_id": room.contact.external_id,
            "created_on": room.created_on.isoformat(),
        }
        self._rooms_client.request_room(content=room_data)

    def _get_project_uuid(self, room: "Room") -> str:
        """Return the UUID of the secondary project if it's Infracommerce, otherwise the principal."""
        if not self._is_infracommerce_with_secondary(room):
            return str(room.project.uuid)
        
        return room.queue.sector.config.get("secondary_project")

    def _is_infracommerce_with_secondary(self, room: "Room") -> bool:
        """Check if it's an Infracommerce project with a secondary project configured."""        
        if not room.project.config:
            return False
        
        if not room.project.config.get("its_principal", False):
            return False
        
        if not (room.queue and room.queue.sector and room.queue.sector.config):
            return False
        
        return bool(room.queue.sector.config.get("secondary_project"))
