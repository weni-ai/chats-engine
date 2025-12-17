from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from chats.apps.api.pagination import CustomCursorPagination
from chats.apps.api.v1.msgs.filters import MessageFilter
from chats.apps.api.v1.msgs.permissions import MessagePermission
from chats.apps.api.v2.msgs.serializers import MessageSerializerV2
from chats.apps.msgs.models import Message as ChatMessage


class MessageViewSetV2(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet v2 for Messages - read-only

    Available endpoints:
    - GET /v2/msg/        - List messages (paginated)

    Returns simplified structure with only essential fields.
    """

    serializer_class = MessageSerializerV2
    permission_classes = [IsAuthenticated, MessagePermission]
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = MessageFilter
    pagination_class = CustomCursorPagination
    lookup_field = "uuid"
    ordering = ["-created_on"]

    def get_queryset(self):
        return ChatMessage.objects.select_related(
            "room",
            "user",
            "contact",
            "internal_note",
            "internal_note__user",
        ).prefetch_related("medias")

    def get_paginated_response(self, data):
        if self.request.query_params.get("reverse_results", False):
            data.reverse()
        return super().get_paginated_response(data)
