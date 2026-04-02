from datetime import timedelta

from django.db.models import (
    Case,
    F,
    IntegerField,
    Value,
    When,
    fields,
)
from django.db.models import CharField
from django.db.models.functions import Concat, Extract, Now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import LimitOffsetPagination

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.internal.rooms.filters import RoomFilter
from chats.apps.api.v2.internal.rooms.serializers import RoomInternalListSerializerV2
from chats.apps.rooms.models import Room


class InternalListRoomsViewSetV2(viewsets.ReadOnlyModelViewSet):
    swagger_tag = "Rooms"
    queryset = Room.objects.all()
    serializer_class = RoomInternalListSerializerV2
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
        "user_full_name",
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
        queryset = (
            super()
            .get_queryset()
            .select_related(
                "user",
                "queue",
                "queue__sector",
                "queue__sector__project",
            )
        )

        annotations = {
            "user_full_name": Concat(
                F("user__first_name"),
                Value(" "),
                F("user__last_name"),
                output_field=CharField(),
            ),
            "queue_time": Case(
                When(
                    added_to_queue_at__isnull=False,
                    then=Now() - F("added_to_queue_at"),
                ),
                default=Value(timedelta(0)),
                output_field=fields.DurationField(),
            ),
            "waiting_time": Case(
                When(
                    added_to_queue_at__isnull=False,
                    user_assigned_at__isnull=False,
                    then=F("user_assigned_at") - F("added_to_queue_at"),
                ),
                default=Value(timedelta(0)),
                output_field=fields.DurationField(),
            ),
            "duration": Case(
                When(
                    is_active=True,
                    user__isnull=False,
                    first_user_assigned_at__isnull=False,
                    then=Now() - F("first_user_assigned_at"),
                ),
                When(
                    is_active=False,
                    ended_at__isnull=False,
                    first_user_assigned_at__isnull=False,
                    then=F("ended_at") - F("first_user_assigned_at"),
                ),
                default=Value(timedelta(0)),
                output_field=fields.DurationField(),
            ),
            "first_response_time": Case(
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
                default=Value(0),
                output_field=IntegerField(),
            ),
        }

        queryset = queryset.annotate(**annotations)

        return queryset
