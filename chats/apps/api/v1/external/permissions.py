from rest_framework import permissions
from chats.apps.projects.models import ProjectPermission


class IsAdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):  # pragma: no cover
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        try:
            auth_token = auth_header.split()[1]
            return (
                True if ProjectPermission.objects.get(pk=auth_token, role=1) else False
            )
        except (AttributeError, ProjectPermission.DoesNotExist):
            return False
