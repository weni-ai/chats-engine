from django.contrib.auth import get_user_model
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from chats.apps.projects.models import Project, ProjectPermission, CustomStatus


def validate_agent_disconnect(request_user, project_uuid: str, agent_email: str):
    if not project_uuid or not agent_email:
        raise NotFound(detail="Required fields not found")

    try:
        project = Project.objects.get(uuid=project_uuid)
    except Project.DoesNotExist:
        raise NotFound(detail="Project not found")

    User = get_user_model()
    try:
        target_user = User.objects.get(email=agent_email)
    except User.DoesNotExist:
        raise NotFound(detail="Agent not found")

    try:
        requester_perm = ProjectPermission.objects.get(
            user=request_user, project=project
        )
    except ProjectPermission.DoesNotExist:
        raise PermissionDenied(detail="Not allowed on this project")
    if not requester_perm.is_admin:
        raise PermissionDenied(detail="Not allowed")

    try:
        target_perm = ProjectPermission.objects.get(
            user=target_user, project=project
        )
    except ProjectPermission.DoesNotExist:
        raise NotFound(detail="Agent permission not found")

    if (
        target_perm.status == ProjectPermission.STATUS_OFFLINE
        and not CustomStatus.objects.filter(
            user=target_user, project=project, is_active=True
        ).exists()
    ):
        raise ValidationError({"detail": "User already disconnected"})

    return project, target_user, target_perm
