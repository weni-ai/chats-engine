from rest_framework import permissions
from chats.apps.projects.models import Flow, ProjectPermission


class IsExternalPermission(permissions.BasePermission):
    def has_permission(self, request, view):  # pragma: no cover
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        try:
            auth_token = auth_header.split()[1]
            return (
                True if ProjectPermission.objects.get(pk=auth_token, role=1) else False
            )
        except (AttributeError, ProjectPermission.DoesNotExist):
            return False


class IsFlowPermission(permissions.BasePermission):
    def has_permission(self, request, view):  # pragma: no cover
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        try:
            auth_token = auth_header.split()[1]
            return True if Flow.objects.get(pk=auth_token) else False
        except (AttributeError, Flow.DoesNotExist):
            return False
