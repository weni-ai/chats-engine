from typing import Dict, Iterable, List, Set, TypedDict
from uuid import UUID

from django.db.models import Count, Q

from chats.apps.projects.models.models import ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room


class AgentCountDict(TypedDict):
    name: str
    uuid: str
    rooms_in_awaiting: int
    rooms_in_progress: int


class RoomsCountByAgentResult(TypedDict):
    agents: List[AgentCountDict]


class RoomsCountByAgentService:
    """
    Builds agent room counts for `rooms_count/by_agent`.

    `uuid` is the user email. `accounts.User` has no uuid field, and email
    is the key used by room assignment.

    `rooms_in_progress` counts active assigned rooms for that user.
    `rooms_in_awaiting` counts active unassigned rooms in queues that
    both the agent and the requester can see.

    Admins see every agent in the project. Sector managers see agents in
    the sectors they manage. Agents see only themselves.

    Agents are ordered by `rooms_in_progress` descending, then by name.
    """

    def get_counts(
        self,
        *,
        project_uuid: UUID,
        requesting_permission: ProjectPermission,
    ) -> RoomsCountByAgentResult:
        permissions = self._visible_permissions(project_uuid, requesting_permission)
        visible_queue_ids = self._requester_queue_ids(
            project_uuid, requesting_permission
        )
        progress_by_user = self._progress_by_user(project_uuid, visible_queue_ids)
        awaiting_by_queue = self._awaiting_by_queue(project_uuid)

        agents = []
        for permission in permissions:
            user = permission.user
            if user is None:
                continue
            queue_ids = self._agent_queue_ids(permission, visible_queue_ids)
            awaiting = sum(awaiting_by_queue.get(queue_id, 0) for queue_id in queue_ids)
            agents.append(
                {
                    "name": self._display_name(user),
                    "uuid": user.email,
                    "rooms_in_awaiting": awaiting,
                    "rooms_in_progress": progress_by_user.get(user.email, 0),
                }
            )

        agents.sort(
            key=lambda agent: (-agent["rooms_in_progress"], agent["name"].casefold())
        )
        return {"agents": agents}

    def _visible_permissions(self, project_uuid: UUID, permission: ProjectPermission):
        queryset = (
            ProjectPermission.objects.filter(
                project__uuid=project_uuid,
                user__isnull=False,
            )
            .select_related("user")
            .prefetch_related(
                "queue_authorizations__queue",
                "sector_authorizations__sector__queues",
            )
        )
        if permission.is_admin:
            return queryset
        if permission.is_manager(any_sector=True):
            sector_ids = permission.sector_authorizations.values_list(
                "sector_id", flat=True
            )
            return queryset.filter(
                Q(pk=permission.pk)
                | Q(sector_authorizations__sector_id__in=sector_ids)
                | Q(queue_authorizations__queue__sector_id__in=sector_ids)
            ).distinct()
        return queryset.filter(pk=permission.pk)

    def _requester_queue_ids(
        self, project_uuid: UUID, permission: ProjectPermission
    ) -> Set[UUID]:
        if permission.is_admin:
            return set(
                Queue.objects.filter(sector__project__uuid=project_uuid).values_list(
                    "uuid", flat=True
                )
            )
        return set(permission.queue_ids)

    def _agent_queue_ids(
        self, permission: ProjectPermission, visible_queue_ids: Set[UUID]
    ) -> Set[UUID]:
        if permission.is_admin:
            return visible_queue_ids

        queue_ids = set()
        for authorization in permission.sector_authorizations.all():
            for queue in authorization.sector.queues.all():
                queue_ids.add(queue.uuid)
        for authorization in permission.queue_authorizations.all():
            if authorization.role == 2:
                continue
            queue_ids.add(authorization.queue_id)
        return queue_ids & visible_queue_ids

    def _progress_by_user(
        self, project_uuid: UUID, visible_queue_ids: Iterable[UUID]
    ) -> Dict[str, int]:
        rows = (
            Room.objects.filter(
                is_active=True,
                is_waiting=False,
                user__isnull=False,
                queue__uuid__in=visible_queue_ids,
                queue__sector__project__uuid=project_uuid,
                queue__is_deleted=False,
                queue__sector__is_deleted=False,
            )
            .values("user_id")
            .annotate(total=Count("pk"))
        )
        return {row["user_id"]: row["total"] for row in rows}

    def _awaiting_by_queue(self, project_uuid: UUID) -> Dict[UUID, int]:
        rows = (
            Room.objects.filter(
                is_active=True,
                is_waiting=False,
                user__isnull=True,
                queue__sector__project__uuid=project_uuid,
                queue__is_deleted=False,
                queue__sector__is_deleted=False,
            )
            .values("queue_id")
            .annotate(total=Count("pk"))
        )
        return {row["queue_id"]: row["total"] for row in rows}

    def _display_name(self, user) -> str:
        name = f"{user.first_name} {user.last_name}".strip()
        return name or user.email
