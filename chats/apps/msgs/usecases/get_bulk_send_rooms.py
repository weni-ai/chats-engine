from django.db.models import QuerySet

from chats.apps.msgs.models import BulkMessageSend
from chats.apps.rooms.models import Room


class GetBulkSendRoomsUseCase:
    """
    Returns the rooms that match a ``BulkMessageSend`` filter snapshot.

    Always scopes to active rooms in the bulk send's project. Optional
    ``queues`` and ``agents`` keys in ``filter_snapshot`` further narrow the
    queryset when non-empty.
    """

    def execute(self, bulk_send: BulkMessageSend) -> "QuerySet[Room]":
        queryset = Room.objects.filter(
            is_active=True,
            queue__sector__project=bulk_send.project,
        )

        filter_snapshot = bulk_send.filter_snapshot or {}
        queues = filter_snapshot.get("queues") or []
        agents = filter_snapshot.get("agents") or []

        if queues:
            queryset = queryset.filter(queue__uuid__in=queues)

        if agents:
            queryset = queryset.filter(user_id__in=agents)

        return queryset
