from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.queues.filters import QueueFlowFilter
from chats.apps.api.v1.external.queues.serializers import QueueFlowSerializer
from chats.apps.api.v1.external.throttling import (
    ExternalHourRateThrottle,
    ExternalMinuteRateThrottle,
    ExternalSecondRateThrottle,
)
from chats.apps.queues.models import Queue


class QueueFlowViewset(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing and retrieving queues via external API.

    Requires project admin authentication via Bearer token.
    Rate limited: 20/sec, 600/min, 30k/hour.
    """

    swagger_tag = "Integrations"
    model = Queue
    queryset = Queue.objects.exclude(is_deleted=True)
    serializer_class = QueueFlowSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = QueueFlowFilter

    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]
    throttle_classes = [
        ExternalSecondRateThrottle,
        ExternalMinuteRateThrottle,
        ExternalHourRateThrottle,
    ]

    def get_queryset(self):
        permission = self.request.auth
        qs = super().get_queryset()
        if permission is None or permission.role != 1:
            return qs.none()
        return qs.filter(sector__project=permission.project)

    def list(self, request, *args, **kwargs):
        """List all active queues in the authenticated project."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve details of a specific queue by UUID."""
        return super().retrieve(request, *args, **kwargs)
