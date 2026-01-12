from rest_framework import permissions
from chats.apps.rooms.models import Room


class CanAddOrRemoveRoomTagPermission(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        room_user = getattr(obj, "user", None)

        if not room_user:
            return False

        return room_user == request.user


class RoomNotePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if view.action not in ["list", "create"]:
            return super().has_permission(request, view)

        room_uuid = request.data.get("room") or request.query_params.get("room")
        room = (
            Room.objects.filter(uuid=room_uuid)
            .select_related("queue__sector__project")
            .first()
        )
        if room:
            if room.user == user:
                return True
            project = room.queue.sector.project
            try:
                permission = user.project_permissions.get(project=project)
            except Exception:
                return False
        else:
            project_uuid = request.query_params.get("project")
            if not project_uuid:
                return False
            try:
                permission = user.project_permissions.get(project__uuid=project_uuid)
            except Exception:
                return False

        return permission.role > 0 if view.action == "list" else False
