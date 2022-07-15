from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from chats.apps.api.v1.sectors.serializers import (
    SectorPermissionSerializer,
    SectorSerializer,
)
from chats.apps.api.v1.rooms.serializers import RoomTagSectorSerializer
from chats.apps.sectors.models import Sector, SectorPermission
from chats.apps.rooms.models import RoomTag


class SectorViewset(viewsets.ModelViewSet):
    queryset = Sector.objects
    serializer_class = SectorSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_sector("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_sector("update")

    def perform_destroy(self, instance):
        instance.notify_sector("destroy")
        super().perform_destroy(instance)


class RoomTagsViewset(viewsets.ModelViewSet):
    queryset = RoomTag.objects
    serializer_class = RoomTagSectorSerializer
    permission_classes = [
        IsAuthenticated,
    ]


class SectorPermissionViewset(viewsets.ModelViewSet):
    queryset = SectorPermission.objects
    serializer_class = SectorPermissionSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_user("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_user("update")

    def perform_destroy(self, instance):
        instance.notify_user("destroy")
        super().perform_destroy(instance)
