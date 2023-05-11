from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.queues import serializers as queue_serializers
from chats.apps.api.v1.queues.filters import QueueFilter
from chats.apps.queues.models import Queue, QueueAuthorization


class QueueInternalViewset(viewsets.ModelViewSet):
    queryset = Queue.objects.all()
    serializer_class = queue_serializers.QueueSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QueueFilter
    permission_classes = [IsAuthenticated, ModuleHasPermission]
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return queue_serializers.QueueReadOnlyListSerializer
        if self.action == "update":
            return queue_serializers.QueueUpdateSerializer

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


class QueueAuthInternalViewset(viewsets.ModelViewSet):
    queryset = QueueAuthorization.objects.all()
    serializer_class = queue_serializers.QueueAuthorizationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "queue",
    ]
    permission_classes = [IsAuthenticated, ModuleHasPermission]
    lookup_field = "uuid"

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return queue_serializers.QueueAuthorizationReadOnlyListSerializer
        if self.action == "update":
            return queue_serializers.QueueAuthorizationUpdateSerializer

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
