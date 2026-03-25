from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.sectors.serializers import SectorFlowSerializer
from chats.apps.api.v1.external.throttling import (
    ExternalHourRateThrottle,
    ExternalMinuteRateThrottle,
    ExternalSecondRateThrottle,
)
from chats.apps.sectors.models import Sector


class SectorFlowViewset(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing and retrieving sectors via external API.

    Requires project admin authentication via Bearer token.
    Rate limited: 20/sec, 600/min, 30k/hour.
    """

    swagger_tag = "Integrations"
    model = Sector
    queryset = Sector.objects.exclude(is_deleted=True)
    serializer_class = SectorFlowSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "name",
    ]
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
        return qs.filter(project=permission.project)

    def list(self, request, *args, **kwargs):
        """List all active sectors in the authenticated project."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve details of a specific sector by UUID."""
        return super().retrieve(request, *args, **kwargs)
