from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from chats.apps.api.v1 import sectorqueue
from chats.apps.api.v1.permissions import (
    ProjectAdminPermission,
    SectorAddQueuePermission,
    SectorAnyPermission,
    SectorAgentReadOnlyPermission,
    SectorDeleteQueuePermission,
    SectorQueueAddAgentPermission
)

from chats.apps.api.v1.sectorqueue import serializers as sectorqueue_serializers
from chats.apps.api.v1.sectors.filters import SectorFilter
from chats.apps.sectorqueue.models import SectorQueue, SectorQueueAuthorization
from chats.apps.api.v1.sectorqueue.filters import SectorQueueFilter


class SectorQueueViewset(viewsets.ModelViewSet):
    queryset = SectorQueue.objects.all()
    serializer_class = sectorqueue_serializers.SectorQueueSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SectorQueueFilter
    permission_classes = [
        IsAuthenticated,
    ]
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in ["create", "update"]:
            permission_classes.append(SectorAddQueuePermission)
        elif self.action in ["list", "retrieve"]:
            permission_classes.append(SectorAgentReadOnlyPermission)
        elif self.action in ["destroy"]:
            permission_classes.append(SectorDeleteQueuePermission)

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == "list":
            return sectorqueue_serializers.SectorQueueReadOnlyListSerializer
        elif self.action == "retrieve":
            return sectorqueue_serializers.SectorQueueReadOnlyListSerializer
        elif self.action == "update":
            return sectorqueue_serializers.SectorQueueUpdateSerializer

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
        # serializer.instance.notify_sector("create")

    def perform_update(self, serializer):
        serializer.save()
        # serializer.instance.notify_sector("update")

    def perform_destroy(self, instance):
        # instance.notify_sector("destroy")
        instance.is_deleted = True
        instance.save()


class SectorQueueAuthorizationViewset(viewsets.ModelViewSet):
    queryset = SectorQueueAuthorization.objects.all()
    serializer_class = sectorqueue.serializers.SectorQueueAuthorizationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in ["create", "update"]:
            permission_classes.append(SectorQueueAddAgentPermission)
        elif self.action in ["list", "retrieve"]:
            permission_classes.append(SectorAgentReadOnlyPermission)
        elif self.action in ["destroy"]:
            permission_classes.append(SectorDeleteQueuePermission)

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save()
        # serializer.instance.notify_user("create")

    def perform_update(self, serializer):
        serializer.save()
        # serializer.instance.notify_user("update")

    def perform_destroy(self, instance):
        # instance.notify_user("destroy")
        super().perform_destroy(instance)
