import logging
from uuid import UUID

from rest_framework import permissions

from chats.apps.projects.models import ProjectPermission
from chats.apps.sectors.models import Sector

logger = logging.getLogger(__name__)


def _is_valid_uuid(value) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


class SectorQuickMessageProjectPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        if view.action == "list":
            project_uuid = request.query_params.get("project")
            sector_uuid = request.query_params.get("sector")

            if project_uuid:
                if not _is_valid_uuid(project_uuid):
                    logger.warning(
                        "Invalid project UUID in sector_quick_messages query params",
                        extra={"project": project_uuid},
                    )
                    return False
                return ProjectPermission.objects.filter(
                    project__uuid=project_uuid, user=request.user
                ).exists()

            if sector_uuid:
                if not _is_valid_uuid(sector_uuid):
                    logger.warning(
                        "Invalid sector UUID in sector_quick_messages query params",
                        extra={"sector": sector_uuid},
                    )
                    return False
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
