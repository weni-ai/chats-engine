from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.permissions import (
    SectorManagerPermission,
)
from chats.apps.api.v1.sectors import serializers as sector_serializers
from chats.apps.api.v1.sectors.filters import SectorFilter
from chats.apps.sectors.models import Sector


class SectorInternalViewset(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = sector_serializers.SectorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SectorFilter
    permission_classes = [
        IsAuthenticated,
    ]
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == "list":
            return sector_serializers.SectorReadOnlyListSerializer
        elif self.action == "retrieve":
            return sector_serializers.SectorReadOnlyRetrieveSerializer
        elif self.action == "update":
            return sector_serializers.SectorUpdateSerializer

        return super().get_serializer_class()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"is_deleted": True},
            status.HTTP_200_OK,
        )

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
