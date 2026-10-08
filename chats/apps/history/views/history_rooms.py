from django.db.models import Func, Value
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Upper
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from chats.apps.rooms.models import Room
from chats.core.filters import DocumentAwareSearchFilter

from ..filters.rooms_filter import HistoryRoomFilter
from ..serializers.rooms import (
    RoomBasicValuesSerializer,
    RoomDetailSerializer,
    RoomHistorySerializer,
)
from .permissions import CanRetrieveRoomHistory


class HistoryRoomViewset(ReadOnlyModelViewSet):
    swagger_tag = "History"
    queryset = Room.objects.select_related(
        "user",
        "contact",
        "queue",
        "queue__sector",
        "queue__sector__project",
        "closed_by",
        "csat_survey",
    ).prefetch_related("tags")

    serializer_class = RoomHistorySerializer
    filter_backends = [
        DjangoFilterBackend,
        DocumentAwareSearchFilter,
        OrderingFilter,
    ]
    filterset_class = HistoryRoomFilter
    permission_classes = [IsAuthenticated]
    search_fields = [
        "contact__name",
        "contact__email",
        "contact__document",
        "custom_fields__email",
        "custom_fields_normalized_document",
        "urn",
        "user__first_name",
        "user__last_name",
        "user__email",
        "protocol",
        "service_chat",
    ]
    ordering = ["-ended_at"]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        if self.request.GET.get("basic", None):
            return Room.objects.values("uuid", "ended_at")

        return (
            super()
            .get_queryset()
            .annotate(
                custom_fields_normalized_document=Upper(
                    Func(
                        KeyTextTransform("document", "custom_fields"),
                        Value("[^A-Za-z0-9]"),
                        Value(""),
                        Value("g"),
                        function="REGEXP_REPLACE",
                    )
                )
            )
        )

    def get_permissions(self):
        permission_classes = self.permission_classes

        if self.action == "retrieve":
            permission_classes = (IsAuthenticated, CanRetrieveRoomHistory)
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.request.GET.get("basic", None):
            return RoomBasicValuesSerializer
        if self.action == "retrieve":
            return RoomDetailSerializer
        return super().get_serializer_class()
