from django.db import models

from .models import Room


def can_retrieve(room, user, project) -> bool:
    filter_project_uuid = models.Q(queue__sector__project__uuid=project)
    is_sector_manager = models.Q(queue__sector__authorizations__permission__user=user)
    is_project_admin = models.Q(
        models.Q(queue__sector__project__permissions__user=user)
        & models.Q(queue__sector__project__permissions__role=1)
    )
    is_user_assigned_to_room = models.Q(user=user)
    check_admin_manager_agent_role_filter = models.Q(
        filter_project_uuid
        & (is_sector_manager | is_project_admin | is_user_assigned_to_room)
    )

    rooms_check = Room.objects.filter(
        check_admin_manager_agent_role_filter,
    ).exists()
    return rooms_check
