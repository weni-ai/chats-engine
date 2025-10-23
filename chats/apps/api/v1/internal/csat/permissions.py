from rest_framework.permissions import BasePermission

from chats.apps.rooms.models import Room
from chats.apps.csat.models import CSATSurvey


class CSATWebhookPermission(BasePermission):
    def has_permission(self, request, view):
        project_uuid = request.auth.get("project")

        if not project_uuid:
            return False

        room_uuid = request.auth.get("room")

        room = Room.objects.filter(
            uuid=room_uuid, queue__sector__project__uuid=project_uuid
        ).first()

        return (
            room
            and not room.is_active
            and not CSATSurvey.objects.filter(room=room).exists()
        )
