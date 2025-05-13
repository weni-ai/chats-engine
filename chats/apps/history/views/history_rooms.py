from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from chats.apps.rooms.models import Room

from ..filters.rooms_filter import HistoryRoomFilter
from ..serializers.rooms import (
    RoomBasicSerializer,
    RoomDetailSerializer,
    RoomHistorySerializer,
)
from .permissions import CanRetrieveRoomHistory


class HistoryRoomViewset(ReadOnlyModelViewSet):
    queryset = Room.objects.select_related(
        "user", "contact", "queue", "queue__sector"
    ).prefetch_related("tags")

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
        "protocol",
        "service_chat",
    ]
    ordering = ["-ended_at"]

    @method_decorator(cache_page(60 * 5))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.GET.get("basic", None):
            return queryset.only("uuid", "ended_at")

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
