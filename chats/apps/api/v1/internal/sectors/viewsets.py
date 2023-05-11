from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.internal.sectors.serializers import SectorTagSerializer
from chats.apps.api.v1.sectors import serializers as sector_serializers
from chats.apps.api.v1.sectors.filters import SectorFilter
from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag


class SectorInternalViewset(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = sector_serializers.SectorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SectorFilter
    permission_classes = [IsAuthenticated, ModuleHasPermission]
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

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()
        return Response(
            {"is_deleted": True},
            status.HTTP_200_OK,
        )


class SectorAuthorizationViewset(viewsets.ModelViewSet):
    queryset = SectorAuthorization.objects.all()
    serializer_class = sector_serializers.SectorAuthorizationSerializer
    permission_classes = [IsAuthenticated, ModuleHasPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "sector",
    ]
    lookup_field = "uuid"

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_user("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_user("update")

    def perform_destroy(self, instance):
        instance.notify_user("destroy")
        super().perform_destroy(instance)


class SectorTagsViewset(viewsets.ModelViewSet):
    queryset = SectorTag.objects.all()
    serializer_class = SectorTagSerializer
    permission_classes = [IsAuthenticated, ModuleHasPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["sector"]
    lookup_field = "uuid"
