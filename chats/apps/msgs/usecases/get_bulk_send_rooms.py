from django.db.models import Q, QuerySet

from chats.apps.msgs.choices import BulkMessageSendRoomStatus
from chats.apps.msgs.models import BulkMessageSend
from chats.apps.rooms.models import Room


class GetBulkSendRoomsUseCase:
    """
    Returns the rooms that match a ``BulkMessageSend`` filter snapshot.

    Always scopes to active rooms in the bulk send's project. Required
    ``statuses`` and optional ``queues`` / ``agents`` keys in
    ``filter_snapshot`` further narrow the queryset when non-empty.
    """

    def execute(self, bulk_send: BulkMessageSend) -> "QuerySet[Room]":
        queryset = Room.objects.filter(
            is_active=True,
            queue__sector__project=bulk_send.project,
        )

        filter_snapshot = bulk_send.filter_snapshot or {}
        queues = filter_snapshot.get("queues") or []
        agents = filter_snapshot.get("agents") or []
        statuses = filter_snapshot.get("statuses") or []

        if queues:
            queryset = queryset.filter(queue__uuid__in=queues)

        if agents:
            queryset = queryset.filter(user__email__in=agents)

        if not statuses:
            return queryset.none()

        status_q = Q()
        if BulkMessageSendRoomStatus.ONGOING in statuses:
            status_q |= Q(user__isnull=False, is_waiting=False)
        if BulkMessageSendRoomStatus.WAITING in statuses:
            status_q |= Q(user__isnull=True, is_waiting=False)

        return queryset.filter(status_q)
