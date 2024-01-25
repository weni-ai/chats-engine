from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from chats.apps.rooms.models import Room

from ..filters.rooms_filter import HistoryRoomFilter
from ..serializers.messages import MessageReportSerializer
from ..serializers.rooms import (
    RoomBasicSerializer,
    RoomDetailSerializer,
    RoomHistorySerializer,
)
from .permissions import CanRetrieveRoomHistory


class HistoryRoomViewset(ReadOnlyModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomHistorySerializer
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]
    filterset_class = HistoryRoomFilter
    permission_classes = [IsAuthenticated]
    search_fields = [
        "contact__name",
        "urn",
        "user__first_name",
        "user__last_name",
        "user__email",
    ]
    ordering = ["-ended_at"]

    def get_permissions(self):
        permission_classes = self.permission_classes

        if self.action == "retrieve":
            permission_classes = (IsAuthenticated, CanRetrieveRoomHistory)
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.request.GET.get("basic", None):
            return RoomBasicSerializer
        if self.action == "retrieve":
            return RoomDetailSerializer
        return super().get_serializer_class()

    @action(
        detail=True,
        methods=["GET"],
        url_name="report-messages",
    )
    def report_messages(self):
        room = self.get_object()
        if room.is_active is True:
            return Response(
                {"detail": "Cannot retrieve the messages report from active rooms"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        messages = room.msgs.all()
        message_values = messages.values(
            "uuid",
            "room",
            "user__email",
            "contact__name",
            "text",
            "media__content_type",
            "media__url",
            "created_on",
        )

        serialized_messages = MessageReportSerializer(message_values, many=True)

        return Response(serialized_messages.data, status=status.HTTP_200_OK)
