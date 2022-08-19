from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from chats.apps.api.v1.permissions import (
    SectorAgentReadOnlyListPermission,
    SectorAgentReadOnlyRetrievePermission
)

from chats.apps.api.v1.queues import serializers as sectorqueue_serializers
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.api.v1.queues.filters import SectorQueueFilter, SectorAuthorizationQueueFilter


class QueueViewset(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    queryset = Queue.objects.all()
    serializer_class = queue_serializers.QueueSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QueueFilter
    permission_classes = []
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in ["list"]:
            permission_classes = [IsAuthenticated, SectorAgentReadOnlyListPermission]
        if self.action in ["retrieve"]:
            permission_classes = [
                IsAuthenticated,
                SectorAgentReadOnlyRetrievePermission,
            ]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == "list":
            return sectorqueue_serializers.SectorQueueReadOnlyListSerializer
        return super().get_serializer_class()


class QueueAuthorizationViewset(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet
):
    queryset = QueueAuthorization.objects.all()
    serializer_class = queue_serializers.QueueAuthorizationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SectorAuthorizationQueueFilter
    permission_classes = []
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in ["list"]:
            permission_classes = [IsAuthenticated, SectorAgentReadOnlyListPermission]
        if self.action in ["retrieve"]:
            permission_classes = [
                IsAuthenticated,
                SectorAgentReadOnlyRetrievePermission,
            ]
        return [permission() for permission in permission_classes]
