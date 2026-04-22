from rest_framework.permissions import BasePermission
from rest_framework.exceptions import ValidationError

from chats.apps.projects.models.models import Project


class JWTRequiredPermission(BasePermission):
    """
    Custom permission class that requires JWT authentication.
    Returns 401 Unauthorized when authentication fails.
    """

    def has_permission(self, request, view):
        return request.auth is not None


class InternalAPITokenRequiredPermission(BasePermission):
    """
    Custom permission class that requires Internal API token authentication.
    Returns 401 Unauthorized when authentication fails.
    """

    def has_permission(self, request, view):
        return getattr(request, "auth", None) == "INTERNAL"


class ProjectUUIDRequestBodyPermission(BasePermission):
    """
    Custom permission class that requires a project UUID in the request body.
    Returns 400 Bad Request when the project UUID is not provided.
    """

    def has_permission(self, request, view):
        project_uuid = request.data.get("project_uuid")

        if not project_uuid:
            raise ValidationError(
                {"project_uuid": ["This field is required"]}, code="required"
            )

        project = Project.objects.filter(uuid=project_uuid).first()

        if not project:
            return False

        if not project.permissions.filter(user=request.user).exists():
            return False

        request.project = project
        return True
