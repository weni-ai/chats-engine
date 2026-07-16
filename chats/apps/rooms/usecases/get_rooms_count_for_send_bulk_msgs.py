from typing import Iterable, Optional, Sequence, Union
from uuid import UUID

from django.db.models import Q

from chats.apps.rooms.models import Room

WAITING = "waiting"
ONGOING = "ongoing"


class GetRoomsCountForSendBulkMsgsUseCase:
    def execute(
        self,
        *,
        project_uuid: Union[UUID, str],
        statuses: Sequence[str],
        queues: Optional[Iterable[Union[UUID, str]]] = None,
        agents: Optional[Iterable[str]] = None,
    ) -> int:
        queryset = Room.objects.filter(
            is_active=True,
            project_uuid=str(project_uuid),
        )

        status_q = Q()
        if WAITING in statuses:
            status_q |= Q(user__isnull=True)
        if ONGOING in statuses:
            status_q |= Q(user__isnull=False)

        if status_q:
            queryset = queryset.filter(status_q)

        queue_list = list(queues) if queues is not None else []
        if queue_list:
            queryset = queryset.filter(queue__uuid__in=queue_list)

        agent_list = list(agents) if agents is not None else []
        if agent_list:
            queryset = queryset.filter(user_id__in=agent_list)

        return queryset.count()
