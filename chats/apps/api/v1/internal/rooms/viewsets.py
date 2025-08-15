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
    search_fields = [
        "contact__external_id",
        "contact__name",
        "user__email",
        "urn",
    ]
    filterset_class = RoomFilter

    pagination_class = LimitOffsetPagination
    pagination_class.page_size = 5

    # def get_queryset(self):
    #     # Exclude rooms with imported_room in config
    #     return super().get_queryset().exclude(config__imported_room=True)
