from typing import List, TypedDict
from uuid import UUID

from django.db.models import Count, Q, QuerySet

from chats.apps.projects.models.models import ProjectPermission
from chats.apps.sectors.models import Sector


class SectorCountDict(TypedDict):
    name: str
    uuid: str
    rooms_in_awaiting: int
    rooms_in_progress: int


class RoomsCountBySectorResult(TypedDict):
    sectors: List[SectorCountDict]


class RoomsCountBySectorService:
    """
    Builds sector room counts for `rooms_count/by_sector`.

    Visibility matches `rooms_count/by_queue` without the optional email
    target: admins see every sector, sector managers see sectors they
    manage, and agents see sectors of their authorized queues.

    A queued room is active, unassigned and already out of flow start.
    An in-service room is active, assigned and out of flow start.
    Managers and admins count every assigned room. Agents count only
    rooms assigned to themselves.

    Sectors are ordered by `rooms_in_progress` descending, then by name.
    """

    def get_counts(
        self,
        *,
        project_uuid: UUID,
        requesting_permission: ProjectPermission,
    ) -> RoomsCountBySectorResult:
        permission = requesting_permission
        show_all_sectors = permission.is_admin
        count_in_service_globally = permission.is_admin or permission.is_manager(
            any_sector=True
        )

        sectors = self._build_sectors_queryset(
            project_uuid=project_uuid,
            permission=permission,
            show_all_sectors=show_all_sectors,
            count_in_service_globally=count_in_service_globally,
        )
        return {
            "sectors": [
                {
                    "name": sector.name,
                    "uuid": str(sector.uuid),
                    "rooms_in_awaiting": sector.rooms_in_awaiting,
                    "rooms_in_progress": sector.rooms_in_progress,
                }
                for sector in sectors
            ]
        }

    def _build_sectors_queryset(
        self,
        *,
        project_uuid: UUID,
        permission: ProjectPermission,
        show_all_sectors: bool,
        count_in_service_globally: bool,
    ) -> QuerySet[Sector]:
        sectors = Sector.objects.filter(project__uuid=project_uuid)
        if not show_all_sectors:
            sectors = sectors.filter(queues__uuid__in=permission.queue_ids).distinct()

        queued_filter = Q(
            queues__rooms__is_active=True,
            queues__rooms__user__isnull=True,
            queues__rooms__is_waiting=False,
            queues__is_deleted=False,
        )
        in_service_filter = Q(
            queues__rooms__is_active=True,
            queues__rooms__is_waiting=False,
            queues__rooms__user__isnull=False,
            queues__is_deleted=False,
        )
        if not count_in_service_globally:
            in_service_filter &= Q(queues__rooms__user=permission.user)

        return sectors.annotate(
            rooms_in_awaiting=Count(
                "queues__rooms", filter=queued_filter, distinct=True
            ),
            rooms_in_progress=Count(
                "queues__rooms", filter=in_service_filter, distinct=True
            ),
        ).order_by("-rooms_in_progress", "name", "uuid")
