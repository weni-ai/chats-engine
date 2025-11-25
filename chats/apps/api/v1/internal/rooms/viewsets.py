from django.db.models import (
    Case,
    ExpressionWrapper,
    F,
    IntegerField,
    Value,
    When,
    fields,
)
from django.db.models.functions import Extract, Now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import LimitOffsetPagination

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.internal.rooms.serializers import RoomInternalListSerializer
from chats.apps.rooms.models import Room

from .filters import RoomFilter


class InternalListRoomsViewSet(viewsets.ReadOnlyModelViewSet):
    swagger_tag = "Rooms"
    queryset = Room.objects.all()
    serializer_class = RoomInternalListSerializer
    lookup_field = "uuid"
    permission_classes = [permissions.IsAuthenticated, ModuleHasPermission]

    filter_backends = [
        filters.OrderingFilter,
        filters.SearchFilter,
        DjangoFilterBackend,
    ]
    ordering = ["-created_on"]
    ordering_fields = [
        "created_on",
        "ended_at",
        "is_active",
        "urn",
        "uuid",
        "user__email",
        "user__first_name",
        "user__last_name",
        "contact__name",
        "queue__name",
        "queue__sector__name",
        "first_user_assigned_at",
        "user_assigned_at",
        "added_to_queue_at",
        "queue_time",
        "waiting_time",
        "duration",
        "first_response_time",
    ]
    search_fields = [
        "contact__external_id",
        "contact__name",
        "user__email",
        "urn",
    ]
    filterset_class = RoomFilter

    pagination_class = LimitOffsetPagination
    pagination_class.page_size = 5

    def get_queryset(self):
        queryset = super().get_queryset()

        queryset = queryset.annotate(
            queue_time=ExpressionWrapper(
                Now() - F("added_to_queue_at"), output_field=fields.DurationField()
            ),
            waiting_time=ExpressionWrapper(
                F("user_assigned_at") - F("added_to_queue_at"),
                output_field=fields.DurationField(),
            ),
            duration=ExpressionWrapper(
                Now() - F("first_user_assigned_at"), output_field=fields.DurationField()
            ),
            first_response_time=Case(
                When(
                    metric__first_response_time__gt=0,
                    then=F("metric__first_response_time"),
                ),
                When(
                    is_active=True,
                    user__isnull=False,
                    first_user_assigned_at__isnull=False,
                    then=Extract(Now() - F("first_user_assigned_at"), "epoch"),
                ),
                default=Value(None),
                output_field=IntegerField(),
            ),
        )

        return queryset.filter(queue__is_deleted=False, queue__sector__is_deleted=False)
