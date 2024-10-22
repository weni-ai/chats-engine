from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.sectors.serializers import SectorFlowSerializer
from chats.apps.sectors.models import Sector


class SectorFlowViewset(viewsets.ReadOnlyModelViewSet):
    model = Sector
    queryset = Sector.objects.exclude(is_deleted=True)
    serializer_class = SectorFlowSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "name",
    ]
    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]

    def get_queryset(self):
        permission = self.request.auth
        qs = super().get_queryset()
        if permission is None or permission.role != 1:
            return qs.none()
        return qs.filter(project=permission.project)
