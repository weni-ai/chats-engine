from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from chats.apps.api.v1.external.permissions import IsFlowPermission
from chats.apps.api.v1.external.sectors.serializers import SectorFlowSerializer
from chats.apps.sectors.models import Sector


def get_permission_token_from_request(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION")
    return auth_header.split()[1]


class SectorFlowViewset(viewsets.ReadOnlyModelViewSet):
    model = Sector
    queryset = Sector.objects.all()
    serializer_class = SectorFlowSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "name",
    ]
    permission_classes = [
        IsFlowPermission,
    ]
    lookup_field = "uuid"

    def get_queryset(self):
        permission = get_permission_token_from_request(self.request)
        qs = super().get_queryset()
        return qs.filter(project__permissions__uuid=permission)
