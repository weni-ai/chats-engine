from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.viewsets import ReadOnlyModelViewSet

from chats.apps.api.v2.external.rooms.filters import ExternalRoomMetricsFilter
from chats.apps.rooms.models import Room
from chats.apps.api.v2.external.rooms.serializers import ExternalRoomMetricsSerializer
from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.throttling import (
    ExternalHourRateThrottle,
    ExternalMinuteRateThrottle,
    ExternalSecondRateThrottle,
)
from chats.apps.api.pagination import CustomCursorPagination


class ExternalRoomMetricsViewSet(ReadOnlyModelViewSet):
    queryset = Room.objects.select_related("user").prefetch_related("messages", "tags")
    serializer_class = ExternalRoomMetricsSerializer
    authentication_classes = [ProjectAdminAuthentication]
    throttle_classes = [
        ExternalSecondRateThrottle,
        ExternalMinuteRateThrottle,
        ExternalHourRateThrottle,
    ]
    filter_backends = [
        filters.OrderingFilter,
        filters.SearchFilter,
        DjangoFilterBackend,
    ]
    pagination_class = CustomCursorPagination
    ordering = "-created_on"
    ordering_fields = ["created_on", "ended_at", "is_active", "urn"]
    search_fields = [
        "contact__external_id",
        "contact__name",
        "user__email",
        "urn",
    ]
    filterset_class = ExternalRoomMetricsFilter

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(queue__sector__project=self.request.auth.project)
        )
