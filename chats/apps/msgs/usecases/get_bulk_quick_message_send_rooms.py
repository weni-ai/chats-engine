from django.db.models import QuerySet

from chats.apps.msgs.models import BulkQuickMessageSend
from chats.apps.rooms.models import Room


class GetBulkQuickMessageSendRoomsUseCase:
    """
    Returns the ongoing rooms that match a ``BulkQuickMessageSend``.

    Always scopes to active, non-waiting rooms assigned to the requesting
    attendant in the bulk send's project, excluding soft-deleted queues and
    sectors. ``contacts`` further narrows the queryset: ``None`` means all
    matching rooms, a non-empty list filters by contact UUID, and an empty
    list returns no rooms.
    """

    def execute(self, bulk_send: BulkQuickMessageSend) -> "QuerySet[Room]":
        queryset = Room.objects.filter(
            is_active=True,
            is_waiting=False,
            user=bulk_send.user,
            queue__sector__project=bulk_send.project,
            queue__is_deleted=False,
            queue__sector__is_deleted=False,
        )

        if bulk_send.contacts is None:
            return queryset

        if not bulk_send.contacts:
            return queryset.none()

        return queryset.filter(contact__uuid__in=bulk_send.contacts)
