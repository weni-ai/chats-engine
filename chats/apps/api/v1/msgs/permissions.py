from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions

from chats.apps.rooms.models import Room


class MessagePermission(permissions.BasePermission):
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
            permission = user.project_permissions.get(project=project)
        else:
            project_uuid = request.query_params.get("project")
            permission = user.project_permissions.get(project__uuid=project_uuid)

        return permission.role > 0 if view.action == "list" else False

    def has_object_permission(self, request, view, message) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False

        return message.room.user == request.user


class MessageMediaPermission(permissions.BasePermission):
    """ """

    def has_permission(self, request, view):
        user = request.user
        action = view.action

        if action == "create":
            room = Room.objects.get(messages__uuid=request.data.get("message"))
            return room.user == request.user
        elif action == "list":
            try:
                room = Room.objects.get(uuid=request.query_params.get("room"))
                if room.user == request.user:
                    return True
                else:
                    permission = user.project_permissions.get(
                        project=room.queue.sector.project
                    )
                    return permission.role > 0
            except Room.DoesNotExist:
                permission = user.project_permissions.get(
                    project__uuid=request.query_params.get("project")
                )
                return permission.role > 0
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False

        return obj.message.room.user == request.user
