from rest_framework.permissions import BasePermission

from chats.apps.rooms.models import Room
from chats.apps.csat.models import CSATSurvey


class CSATWebhookPermission(BasePermission):
    def has_permission(self, request, view):
        print("[CSATWebhookPermission] request", vars(request))

        project_uuid = request.auth.get("project")

        print("[CSATWebhookPermission] project_uuid", project_uuid)

        if not project_uuid:
            print("[CSATWebhookPermission] project_uuid not found")
            return False

        room_uuid = request.data.get("room")
        auth_room_uuid = request.auth.get("room")

        if room_uuid != auth_room_uuid:
            return False

        print("[CSATWebhookPermission] room_uuid", room_uuid)

        room = Room.objects.filter(
            uuid=room_uuid, queue__sector__project__uuid=project_uuid
        ).first()
        csat_survey = CSATSurvey.objects.filter(room=room).first()
        is_completed = csat_survey.is_completed if csat_survey else False

        return room and not room.is_active and not is_completed
