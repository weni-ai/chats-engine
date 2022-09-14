from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


from chats.apps.projects.models import ProjectPermission
from chats.apps.api.v1.external.agents.serializers import AgentFlowSerializer
from chats.apps.api.v1.external.agents.filters import AgentFlowFilter
from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)


def get_permission_token_from_request(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION")
    return auth_header.split()[1]


class AgentFlowViewset(viewsets.ReadOnlyModelViewSet):
    model = ProjectPermission
    queryset = ProjectPermission.objects.all()
    serializer_class = AgentFlowSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AgentFlowFilter
    permission_classes = [
        IsAuthenticated,
    ]
    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]

    def get_queryset(self):
        permission = get_permission_token_from_request(self.request)
        qs = super().get_queryset()
        return qs.filter(project__permissions=permission, project__permissions__role=1)
