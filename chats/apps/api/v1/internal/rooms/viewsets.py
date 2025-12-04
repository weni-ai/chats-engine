from django.db.models import (
    Case,
    F,
    IntegerField,
    Value,
    When,
    fields,
)
from django.db.models import Q
from django.db.models.functions import Extract, Now, Concat
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.filters import SearchFilter, OrderingFilter

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.internal.rooms.serializers import (
    RoomInternalListSerializer,
    InternalProtocolRoomsSerializer,
)
from chats.apps.rooms.models import Room
from chats.apps.api.pagination import CustomCursorPagination

from chats.apps.api.v1.internal.rooms.filters import (
    RoomFilter,
    InternalProtocolRoomsFilter,
)
from datetime import timedelta


class InternalListRoomsViewSet(viewsets.ReadOnlyModelViewSet):
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
        "protocol",
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

        annotations = {
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

        return queryset.filter(queue__is_deleted=False, queue__sector__is_deleted=False)


class InternalProtocolRoomsViewSet(ListModelMixin, GenericViewSet):
    queryset = Room.objects.all()
    serializer_class = InternalProtocolRoomsSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = InternalProtocolRoomsFilter
    permission_classes = [permissions.IsAuthenticated, ModuleHasPermission]
    search_fields = ["protocol"]
    ordering = ["protocol"]
    ordering_fields = ["protocol"]
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        return super().get_queryset().exclude(Q(protocol__isnull=True) | Q(protocol=""))
