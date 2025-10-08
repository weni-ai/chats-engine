from django.db.models import F, ExpressionWrapper, fields
from django.db.models.functions import Now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import LimitOffsetPagination

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.internal.rooms.serializers import RoomInternalListSerializer
from chats.apps.rooms.models import Room

from .filters import RoomFilter


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
                Now() - F('added_to_queue_at'),
                output_field=fields.DurationField()
            ),
            waiting_time=ExpressionWrapper(
                F('user_assigned_at') - F('added_to_queue_at'),
                output_field=fields.DurationField()
            ),
            duration=ExpressionWrapper(
                Now() - F('first_user_assigned_at'),
                output_field=fields.DurationField()
            )
        )
        
        return queryset.filter(
            queue__is_deleted=False,
            queue__sector__is_deleted=False
        )