import json

from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from rest_framework import mixins, permissions, status
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from chats.apps.api.v1.rooms.serializers import RoomSerializer, TransferRoomSerializer
from chats.apps.rooms.models import Room
from chats.apps.api.v1.sectors import filters as sector_filters
from chats.apps.api.v1 import permissions as api_permissions


class RoomViewset(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        api_permissions.SectorAnyPermission,
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return TransferRoomSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        qs = self.queryset
        return qs.filter(
            Q(user=self.request.user) | Q(user__isnull=True),
            sector__id__in=self.request.user.sector_ids,
            is_active=True,
        )

    @action(detail=True, methods=["PUT"], url_name="close")
    def close(
        self, request, *args, **kwargs
    ):  # TODO: Remove the body options on swagger as it won't use any
        """
        Close a room, setting the ended_at date and turning the is_active flag as false
        """
        # Add send room notification to the channels group
        instance = self.get_object()
        tags = request.data.get("tags", None)
        instance.close(tags, "agent")
        serialized_data = RoomSerializer(instance=instance)
        instance.notify_sector("close")
        return Response(serialized_data.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_sector("create")

    def perform_update(self, serializer):
        transfer_history = self.get_object().transfer_history
        transfer_history = (
            [] if transfer_history is None else json.loads(transfer_history)
        )
        user = serializer.data.get("user")
        sector = serializer.data.get("sector")
        if user:
            _content = {"type": "user", "id": user}
            transfer_history.append(_content)
        if sector:
            _content = {"type": "sector", "id": sector}
            transfer_history.append(_content)

        serializer.save(transfer_history=json.dumps(transfer_history))

        serializer.instance.notify_room("update")

    def perform_destroy(self, instance):
        instance.notify_room("destroy")
        super().perform_destroy(instance)
