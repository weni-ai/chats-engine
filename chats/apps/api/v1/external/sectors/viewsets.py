from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.permissions import IsAdminPermission
from chats.apps.api.v1.external.sectors.serializers import SectorFlowSerializer
from chats.apps.sectors.models import Sector


def get_permission_token_from_request(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION")
    return auth_header.split()[1]


class SectorFlowViewset(viewsets.ReadOnlyModelViewSet):
    model = Sector
    queryset = Sector.objects.exclude(is_deleted=True)
    serializer_class = SectorFlowSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "name",
    ]
    permission_classes = [
        IsAdminPermission,
    ]
    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]

    def get_queryset(self):
        permission = get_permission_token_from_request(self.request)
        qs = super().get_queryset()
        return qs.filter(project__permissions__uuid=permission)
