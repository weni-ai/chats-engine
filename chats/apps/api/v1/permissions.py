from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectorqueue.models import SectorQueue, SectorQueueAuthorization
from chats.apps.sectors.models import SectorAuthorization

WRITE_METHODS = ["POST"]
OBJECT_METHODS = ["DELETE", "PATCH", "PUT", "GET"]


# class ProjectAdminORSectorManager(permissions.BasePermission):


class SectorAnyPermission(permissions.BasePermission):
    """
    Grant permission if the user has *any roles(manager or agent)* in the Sector
    Each model that uses this permission, need to implement a `get_permission` method
    to check the user roles within the sector.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = obj.get_permission(request.user)
        except SectorAuthorization.DoesNotExist:
            return False
        return authorization.is_authorized


class SectorManagerPermission(permissions.BasePermission):
    """
    Grant permission if the user has *manager role* in the Sector or *admin role* in the project
    Each model that uses this permission, need to implement a `get_permission` method
    to check the user roles within the sector.
    """

    def has_object_permission(self, request, view, obj) -> bool:

        if isinstance(request.user, AnonymousUser):
            return False

        try:
            authorization = obj.get_permission(request.user)
        except SectorAuthorization.DoesNotExist:
            return False
        return authorization.can_edit


class ProjectAdminPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = obj.get_permission(request.user)
        except ProjectPermission.DoesNotExist:
            return False
        return authorization.can_edit


class ProjectExternalPermission(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        sector_uuid = request.query_params.get("project")
        try:
            project = Project.objects.get(uuid=sector_uuid)
            authorization = project.get_permission(request.user)
        except (ProjectPermission.DoesNotExist, Project.DoesNotExist):
            return False
        return authorization.is_external

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


class SectorAgentReadOnlyPermission(permissions.BasePermission):
    """
    Grant permission if the user has *agent_role* in the Sector Queue
    Each model that uses this permission, need to implement a `get_permission` method
    to check the user roles within the sector.
    """

    def has_object_permission(self, request, view, obj) -> bool:

        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = obj.get_permission(request.user)
        except SectorQueueAuthorization.DoesNotExist:
            return False
        return authorization


class SectorAddQueuePermission(permissions.BasePermission):
    """
    Grant permission if the user has *manager role* or Sector or *admin role* on Project
    Each model that uses this permission, need to implement a `get_permission` method
    to check the user roles within the sector.
    """

    def has_permission(self, request, view) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            sector_queue = SectorQueue.objects.filter(sector=request.data["sector"]).first()
            authorization = sector_queue.get_permission(request.user)
        except SectorQueue.DoesNotExist:
            return False
        return authorization


class SectorDeleteQueuePermission(permissions.BasePermission):
    """
    Grant permission if the user has *manager role* or Sector or *admin role* Sector of queue
    Each model that uses this permission, need to implement a `get_permission` method
    to check the user roles within the sector.
    """

    def has_object_permission(self, request, view, obj) -> bool:

        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = obj.get_permission(request.user)
        except SectorQueue.DoesNotExist:
            return False
        return authorization


class SectorQueueAddAgentPermission(permissions.BasePermission):
    """
    Grant permission to add agent in queue if the user has *manager role* or Sector or *admin role* on Project
    Each model that uses this permission, need to implement a `get_permission` method
    to check the user roles within the sector.
    """

    def has_permission(self, request, view) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            user = SectorAuthorization.objects.filter(user=request.user).first()
            if not user:
                return False
            authorization = user.get_permission(request.user)
        except SectorQueue.DoesNotExist:
            return False
        return authorization
