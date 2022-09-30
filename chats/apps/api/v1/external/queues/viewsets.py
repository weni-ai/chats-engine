from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets


from chats.apps.queues.models import Queue
from chats.apps.api.v1.external.queues.serializers import QueueFlowSerializer
from chats.apps.api.v1.external.queues.filters import QueueFlowFilter
from chats.apps.api.v1.external.permissions import IsAdminPermission
from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)


def get_permission_token_from_request(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION")
    return auth_header.split()[1]


class QueueFlowViewset(viewsets.ReadOnlyModelViewSet):
    model = Queue
    queryset = Queue.objects.all()
    serializer_class = QueueFlowSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QueueFlowFilter
    permission_classes = [
        IsAdminPermission,
    ]
    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]

    def get_queryset(self):
        permission = get_permission_token_from_request(self.request)
        qs = super().get_queryset()

        return qs.filter(sector__project__permissions__uuid=permission)
