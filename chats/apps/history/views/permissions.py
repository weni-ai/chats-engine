from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions

from chats.apps.projects.models import ProjectPermission
from chats.core.permissions import GetPermission


class CanRetrieveRoomHistory(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action in ["list", "create"]:
            permission = GetPermission(request).permission
            return permission.is_admin

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            perm = obj.get_permission(request.user)
        except ProjectPermission.DoesNotExist:
            return False
        return perm.is_admin
