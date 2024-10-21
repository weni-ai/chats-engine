from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.queues.filters import QueueFlowFilter
from chats.apps.api.v1.external.queues.serializers import QueueFlowSerializer
from chats.apps.queues.models import Queue


class QueueFlowViewset(viewsets.ReadOnlyModelViewSet):
    model = Queue
    queryset = Queue.objects.exclude(is_deleted=True)
    serializer_class = QueueFlowSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QueueFlowFilter

    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]

    def get_queryset(self):
        permission = self.request.auth
        qs = super().get_queryset()
        if permission is None or permission.role != 1:
            return qs.none()
        return qs.filter(sector__project=permission.project)
