from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.queues import serializers as sectorqueue_serializers
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.api.v1.queues.filters import SectorQueueFilter


class QueueInternalViewset(viewsets.ModelViewSet):
    queryset = Queue.objects.all()
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

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return sectorqueue_serializers.SectorQueueReadOnlyListSerializer
        if self.action == "update":
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
        return Response(
            {"is_deleted": True},
            status.HTTP_200_OK,
        )


class QueueAuthInternalViewset(viewsets.ModelViewSet):
    queryset = QueueAuthorization.objects.all()
    serializer_class = sectorqueue_serializers.SectorQueueAuthorizationSerializer
    filter_backends = [DjangoFilterBackend]
    permission_classes = [
        IsAuthenticated,
    ]
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return sectorqueue_serializers.QueueAuthorizationReadOnlyListSerializer
        if self.action == "update":
            return sectorqueue_serializers.QueueAuthorizationUpdateSerializer

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
        return Response(
            {"is_deleted": True},
            status.HTTP_200_OK,
        )
