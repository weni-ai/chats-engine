from rest_framework import permissions

from chats.apps.projects.models import ProjectPermission
from chats.apps.sectors.models import Sector


class SectorQuickMessageProjectPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        if view.action == "list":
            project_uuid = request.query_params.get("project")
            sector_uuid = request.query_params.get("sector")

            if project_uuid:
                return ProjectPermission.objects.filter(
                    project__uuid=project_uuid, user=request.user
                ).exists()

            if sector_uuid:
                try:
                    sector = Sector.objects.get(uuid=sector_uuid)
                except Sector.DoesNotExist:
                    return False
                return ProjectPermission.objects.filter(
                    project=sector.project, user=request.user
                ).exists()

            return True

        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_anonymous:
            return False

        if obj.sector is None:
            return False

        return ProjectPermission.objects.filter(
            project=obj.sector.project, user=request.user
        ).exists()
