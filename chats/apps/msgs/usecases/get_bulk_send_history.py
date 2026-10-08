from typing import Optional, Union
from uuid import UUID

from django.db.models import QuerySet

from chats.apps.msgs.models import BulkMessageSendMessage


class GetBulkSendHistoryUseCase:
    """
    Returns the bulk-send message history queryset for a project.

    Optional ``params`` keys (``start_date``, ``end_date``, ``sender``,
    ``status``) further narrow the queryset when present.
    """

    def execute(
        self,
        project_uuid: Union[UUID, str],
        params: Optional[dict] = None,
    ) -> "QuerySet[BulkMessageSendMessage]":
        params = params or {}

        queryset = (
            BulkMessageSendMessage.objects.filter(
                bulk_message_send__project__uuid=project_uuid
            )
            .select_related(
                "room__contact",
                "room__queue",
                "bulk_message_send__user",
            )
            .order_by("-created_on")
        )

        if start_date := params.get("start_date"):
            queryset = queryset.filter(created_on__date__gte=start_date)
        if end_date := params.get("end_date"):
            queryset = queryset.filter(created_on__date__lte=end_date)
        if sender := params.get("sender"):
            queryset = queryset.filter(bulk_message_send__user__email=sender)
        if status := params.get("status"):
            queryset = queryset.filter(status=status)

        return queryset
