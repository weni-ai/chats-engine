from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions

from chats.apps.projects.models import ProjectPermission
from chats.apps.sectors.models import SectorAuthorization

WRITE_METHODS = ["POST"]
OBJECT_METHODS = ["DELETE", "PATCH", "PUT", "GET"]


class SectorAnyPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = obj.get_permission(
                request.user
            ).exists()  # each and every model that users this permission have to implement this method
        except SectorAuthorization.DoesNotExist:
            return False
        return authorization.is_authorized


class SectorManagerPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = obj.get_permission(
                request.user
            )  # each and every model that users this permission have to implement this method
        except SectorAuthorization.DoesNotExist:
            return False
        return authorization.is_manager


class ProjectAdminPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = obj.get_permission(
                request.user
            )  # each and every model that users this permission have to implement this method
        except ProjectPermission.DoesNotExist:
            return False
        return authorization.is_admin


class ProjectExternalPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = obj.get_permission(
                request.user
            )  # each and every model that users this permission have to implement this method
        except ProjectPermission.DoesNotExist:
            return False
        return authorization.is_external
