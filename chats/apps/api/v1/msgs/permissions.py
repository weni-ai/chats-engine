from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext_lazy as _

from chats.apps.projects.models import ProjectPermission
from chats.apps.rooms.models import Room

RESTRICT_OFFLINE_AGENTS = "restrict_offline_agents"


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
            try:
                permission = user.project_permissions.get(project=project)
            except ProjectPermission.DoesNotExist:
                return False
        else:
            project_uuid = request.query_params.get("project")

            if not project_uuid:
                return False

            permission = user.project_permissions.filter(
                project__uuid=project_uuid
            ).first()

            if not permission:
                return False

        return permission.role > 0 if view.action == "list" else False

    def has_object_permission(self, request, view, message) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False

        room = message.room
        if room.user == request.user:
            return True

        if not room.queue:
            return False

        project = room.queue.sector.project
        return request.user.project_permissions.filter(
            project=project, role__gt=0
        ).exists()


class MessageMediaPermission(permissions.BasePermission):
    """ """

    def has_permission(self, request, view):
        user = request.user
        action = view.action

        if action == "create":
            room = Room.objects.get(messages__uuid=request.data.get("message"))
            return room.user == request.user
        elif action == "list":
            room_uuid = request.query_params.get("room")
            project_uuid = request.query_params.get("project")

            if not room_uuid and not project_uuid:
                raise ValidationError(
                    {
                        "error": [
                            _("Either room or project query parameter is required")
                        ]
                    },
                    code="required",
                )

            room_query = Room.objects.filter(uuid=room_uuid)
            room_user_pk, room_project_uuid = (
                (
                    room_query.values_list(
                        "user__pk",
                        "queue__sector__project__uuid",
                    ).first()
                )
                if room_query.exists()
                else (None, None)
            )

            if room_uuid and (room_project_uuid or project_uuid):
                if room_user_pk == request.user.pk:
                    return True
                else:
                    return user.project_permissions.filter(
                        project__uuid=room_project_uuid, role__gt=0
                    ).exists()
            else:
                if not project_uuid:
                    return False

                return user.project_permissions.filter(
                    project__uuid=project_uuid, role__gt=0
                ).exists()
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False

        room = obj.message.room
        if room.user == request.user:
            return True

        if not room.queue:
            return False

        project = room.queue.sector.project
        return request.user.project_permissions.filter(
            project=project, role__gt=0
        ).exists()


class RestrictOfflineAgents(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action != "create":
            return True

        room_uuid = request.data.get("room")
        if not room_uuid:
            return True

        room = (
            Room.objects.filter(uuid=room_uuid)
            .select_related("queue__sector__project")
            .first()
        )
        if not room or not room.queue:
            return True

        project = room.queue.sector.project
        if not project.get_config(RESTRICT_OFFLINE_AGENTS, False):
            return True

        is_online = request.user.project_permissions.filter(
            project=project,
            status=ProjectPermission.STATUS_ONLINE,
        ).exists()

        if not is_online:
            raise PermissionDenied(
                detail={
                    "error_code": "agent_offline",
                    "error_message": _(
                        "Offline agents cannot send messages in this project"
                    ),
                }
            )

        return True
