from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from chats.apps.api.v1.permissions import IsSectorManager
from chats.apps.api.v1.queues import serializers as queue_serializers
from chats.apps.api.v1.queues.filters import QueueFilter, QueueAuthorizationFilter
from chats.apps.queues.models import Queue, QueueAuthorization


class QueueViewset(ModelViewSet):
    queryset = Queue.objects.all()
    serializer_class = queue_serializers.QueueSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QueueFilter
    permission_classes = [
        IsAuthenticated,
        IsSectorManager,
    ]

    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == "list":
            return queue_serializers.QueueReadOnlyListSerializer
        return super().get_serializer_class()


class QueueAuthorizationViewset(ModelViewSet):
    queryset = QueueAuthorization.objects.all()
    serializer_class = queue_serializers.QueueAuthorizationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QueueAuthorizationFilter
    filterset_fields = [
        "queue",
    ]
    permission_classes = [
        IsAuthenticated,
        IsSectorManager,
    ]
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return queue_serializers.QueueAuthorizationReadOnlyListSerializer
        return super().get_serializer_class()
