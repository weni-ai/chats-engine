from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions

from chats.apps.projects.models import ProjectPermission
from chats.apps.rooms.models import Room
from chats.core.permissions import GetPermission

WRITE_METHODS = ["POST"]
OBJECT_METHODS = ["DELETE", "PATCH", "PUT", "GET"]


class IsProjectAdmin(permissions.BasePermission):
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


class IsSectorManager(permissions.BasePermission):
    def has_permission(self, request, view):
        data = request.data or request.query_params
        if view.action in ["list", "create"]:
            permission = GetPermission(request).permission
            kwargs = {"sector": data.get("sector"), "queue": data.get("queue")}
            return permission.is_manager(**kwargs)

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            perm = obj.get_permission(request.user)
        except ProjectPermission.DoesNotExist:
            return False
        return perm.is_manager(sector=str(obj.sector.pk))


class ProjectAnyPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        return obj.permissions.filter(user=request.user).exists()


class AnyQueueAgentPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        try:
            return GetPermission(request).permission.is_agent(
                queue=None, any_queue=True
            )
        except AttributeError:
            return False


class IsQueueAgent(permissions.BasePermission):
    def has_permission(self, request, view):
        data = request.data or request.query_params
        queue = data.get("queue")
        sector = data.get("sector")

        if view.action in ["list", "create"]:
            permission = GetPermission(request).permission
            return (
                permission.is_agent(queue) if queue else permission.is_manager(sector)
            )

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        if isinstance(obj, Room):
            if obj.user == request.user:
                return True
        try:
            perm = obj.get_permission(request.user)
        except ProjectPermission.DoesNotExist:
            return False
        try:
            return perm.is_agent(str(obj.queue.pk))
        except ObjectDoesNotExist:
            return False


class HasAgentPermissionAnyQueueSector(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        is_admin = obj.project.get_permission(user)

        if is_admin and is_admin.is_manager(obj.pk):
            return True

        return request.user in obj.queue_agents


class HasDashboardAccess(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            project_permission = obj.permissions.get(user=request.user)
            if (
                project_permission.role == 1
                or project_permission.sector_authorizations.exists()
            ):
                return True
        except ProjectPermission.DoesNotExist:
            return False

        return False
