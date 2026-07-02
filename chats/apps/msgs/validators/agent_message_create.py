from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions as drf_exceptions

from chats.apps.api.v1.msgs.permissions import RESTRICT_OFFLINE_AGENTS
from chats.apps.msgs.exceptions import MessageCreateError
from chats.apps.projects.models import ProjectPermission
from chats.apps.rooms.models import Room


def validate_agent_can_create_message(user, room: Room) -> None:
    if room.user != user:
        raise MessageCreateError(
            "permission_denied",
            _("You do not have permission to send messages in this room"),
        )

    if not room.queue:
        return

    project = room.queue.sector.project
    if not project.get_config(RESTRICT_OFFLINE_AGENTS, False):
        return

    is_online = user.project_permissions.filter(
        project=project,
        status=ProjectPermission.STATUS_ONLINE,
    ).exists()

    if not is_online:
        raise MessageCreateError(
            "agent_offline",
            _("Offline agents cannot send messages in this project"),
        )


def first_serializer_error(errors) -> str:
    if isinstance(errors, dict):
        for value in errors.values():
            if isinstance(value, list) and value:
                return str(value[0])
            if isinstance(value, dict):
                nested = first_serializer_error(value)
                if nested:
                    return nested
            elif value:
                return str(value)
    elif isinstance(errors, list) and errors:
        return str(errors[0])
    return str(errors)


def map_save_validation_error(
    error: drf_exceptions.ValidationError,
) -> MessageCreateError:
    detail = error.detail
    message = first_serializer_error(detail)
    normalized = message.lower()

    if "closed rooms cannot receive messages" in normalized:
        return MessageCreateError("room_closed", message)
    if "24h" in normalized:
        return MessageCreateError("message_window_expired", message)

    return MessageCreateError("validation_error", message, details=detail)
