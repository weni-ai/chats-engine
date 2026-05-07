from itertools import groupby
from typing import List, Optional, TypedDict
from uuid import UUID

from django.db.models import Count, Q
from django.db.models.query import QuerySet

from chats.apps.projects.models.models import ProjectPermission
from chats.apps.queues.models import Queue


class QueueCountDict(TypedDict):
    uuid: str
    name: str
    rooms_in_awaiting: int
    rooms_in_progress: int


class SectorCountDict(TypedDict):
    name: str
    queues: List[QueueCountDict]


class RoomsCountByQueueResult(TypedDict):
    sectors: List[SectorCountDict]


class RoomsCountByQueueService:
    """
    Builds the {sectors -> queues -> counts} structure used by the
    `rooms_count/by_queue` endpoint, applying permission-aware filtering.

    Visibility rules:
        - No `email` provided and requester is admin: every sector and
          queue of the project is included; counts are global.
        - No `email` provided and requester is a sector manager: only
          queues from sectors they manage are included; `rooms_in_progress`
          counts every assigned room in those queues (global, not filtered
          by the manager's user).
        - No `email` provided and requester is an agent: only authorized
          queues; `rooms_in_progress` only counts rooms assigned to the
          requester.
        - `email` provided: queue visibility follows the target user's
          authorizations and `rooms_in_progress` always counts only rooms
          assigned to the target user, regardless of the target's role.

    A "queued" room is an active room without an assigned agent that
    has already left the flow start phase
    (`is_active=True, user__isnull=True, is_waiting=False`).

    An "in service" room is an active room with an assigned agent
    (`is_active=True, user__isnull=False, is_waiting=False`).
    """

    def get_counts(
        self,
        *,
        project_uuid: UUID,
        requesting_permission: ProjectPermission,
        target_email: Optional[str] = None,
    ) -> RoomsCountByQueueResult:
        permission, in_service_user_filter, has_target_email = self._resolve_target(
            project_uuid=project_uuid,
            requesting_permission=requesting_permission,
            target_email=target_email,
        )

        # Only project admins see every queue of the project; sector
        # managers are restricted to queues from sectors they manage
        # (handled via `permission.queue_ids`).
        show_all_project_queues = not has_target_email and permission.is_admin

        # Both admins and sector managers count `in_service` globally
        # across the queues they can see. Plain agents and email-targeted
        # views only count rooms assigned to that user.
        count_in_service_globally = not has_target_email and (
            permission.is_admin or permission.is_manager(any_sector=True)
        )

        queues_qs = self._build_queues_queryset(
            project_uuid=project_uuid,
            permission=permission,
            show_all_project_queues=show_all_project_queues,
            count_in_service_globally=count_in_service_globally,
            in_service_user_filter=in_service_user_filter,
        )

        return {"sectors": self._group_into_sectors(queues_qs)}

    def _resolve_target(
        self,
        *,
        project_uuid: UUID,
        requesting_permission: ProjectPermission,
        target_email: Optional[str],
    ):
        if not target_email:
            return (
                requesting_permission,
                Q(rooms__user=requesting_permission.user),
                False,
            )

        normalized_email = target_email.lower()
        permission = ProjectPermission.objects.get(
            user_id=normalized_email,
            project__uuid=project_uuid,
        )
        return permission, Q(rooms__user_id=normalized_email), True

    def _build_queues_queryset(
        self,
        *,
        project_uuid: UUID,
        permission: ProjectPermission,
        show_all_project_queues: bool,
        count_in_service_globally: bool,
        in_service_user_filter: Q,
    ) -> QuerySet[Queue]:
        queues_qs = Queue.objects.filter(
            sector__project__uuid=project_uuid,
            sector__is_deleted=False,
        )
        if not show_all_project_queues:
            queues_qs = queues_qs.filter(uuid__in=permission.queue_ids)

        queued_filter = Q(
            rooms__is_active=True,
            rooms__user__isnull=True,
            rooms__is_waiting=False,
        )
        in_service_filter = (
            Q(
                rooms__is_active=True,
                rooms__is_waiting=False,
                rooms__user__isnull=False,
            )
            if count_in_service_globally
            else Q(rooms__is_active=True, rooms__is_waiting=False)
            & in_service_user_filter
        )

        return (
            queues_qs.select_related("sector")
            .annotate(annotated_queued_rooms_count=Count("rooms", filter=queued_filter))
            .annotate(
                annotated_in_service_rooms_count=Count(
                    "rooms", filter=in_service_filter
                )
            )
            .order_by("sector__name", "sector__uuid", "name")
        )

    def _group_into_sectors(self, queues_qs: QuerySet[Queue]) -> List[SectorCountDict]:
        return [
            {
                "name": sector.name,
                "queues": [
                    {
                        "uuid": str(queue.uuid),
                        "name": queue.name,
                        "rooms_in_awaiting": queue.annotated_queued_rooms_count,
                        "rooms_in_progress": queue.annotated_in_service_rooms_count,
                    }
                    for queue in group
                ],
            }
            for sector, group in groupby(queues_qs, key=lambda q: q.sector)
        ]
