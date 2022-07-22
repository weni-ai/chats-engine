from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.rooms.serializers import RoomTagSectorSerializer
from chats.apps.api.v1.sectors import serializers as sector_serializers
from chats.apps.projects.models import ProjectPermission
from chats.apps.rooms.models import RoomTag
from chats.apps.sectors.models import Sector, SectorAuthorization
from chats.apps.api.v1.permissions import (
    ProjectAdminPermission,
    SectorManagerPermission,
)
from chats.apps.api.v1.sectors.filters import SectorFilter


class SectorViewset(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = sector_serializers.SectorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SectorFilter
    permission_classes = [IsAuthenticated, ProjectAdminPermission]

    def get_serializer_class(self):
        if self.action == "list":
            return sector_serializers.SectorReadOnlyListSerializer
        elif self.action == "retrieve":
            return sector_serializers.SectorReadOnlyRetrieveSerializer

        return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_sector("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_sector("update")

    def perform_destroy(self, instance):
        instance.notify_sector("destroy")
        instance.is_deleted = True
        instance.save()
        return Response(
            {"is_deleted": True},
            status.HTTP_200_OK,
        )


class RoomTagsViewset(viewsets.ModelViewSet):
    queryset = RoomTag.objects
    serializer_class = RoomTagSectorSerializer
    permission_classes = [
        IsAuthenticated,
    ]


class SectorAuthorizationViewset(viewsets.ModelViewSet):
    queryset = SectorAuthorization.objects
    serializer_class = sector_serializers.SectorAuthorizationSerializer
    permission_classes = [IsAuthenticated, SectorManagerPermission]

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_user("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_user("update")

    def perform_destroy(self, instance):
        instance.notify_user("destroy")
        super().perform_destroy(instance)
