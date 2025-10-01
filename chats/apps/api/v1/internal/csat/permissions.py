from rest_framework.permissions import BasePermission

from chats.apps.rooms.models import Room
from chats.apps.csat.models import CSATSurvey


class CSATWebhookPermission(BasePermission):
    def has_permission(self, request, view):
        project_uuid = request.auth.get("project")

        print("[CSATWebhookPermission] project_uuid", project_uuid)

        if not project_uuid:
            print("[CSATWebhookPermission] project_uuid not found")
            return False

        room_uuid = request.data.get("room")

        print("[CSATWebhookPermission] room_uuid", room_uuid)

        room = Room.objects.filter(
            uuid=room_uuid, queue__sector__project__uuid=project_uuid
        ).first()

        print("[CSATWebhookPermission] room", vars(room) if room else "not found")

        return (
            room
            and not room.is_active
            and not CSATSurvey.objects.filter(room=room).exists()
        )
