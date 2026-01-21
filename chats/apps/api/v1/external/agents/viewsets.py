from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.agents.filters import AgentFlowFilter
from chats.apps.api.v1.external.agents.serializers import AgentFlowSerializer
from chats.apps.projects.models import ProjectPermission


class AgentFlowViewset(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing and retrieving agents (project permissions) via external API.

    Requires project admin authentication via Bearer token.
    """

    swagger_tag = "Integrations"
    model = ProjectPermission
    queryset = ProjectPermission.objects.all()
    serializer_class = AgentFlowSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AgentFlowFilter
    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]

    def get_queryset(self):
        permission = self.request.auth
        qs = super().get_queryset()
        if permission is None or permission.role != 1:
            return qs.none()
        return qs.filter(project=permission.project)

    def list(self, request, *args, **kwargs):
        """List all agents (users with permissions) in the authenticated project."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve details of a specific agent by UUID."""
        return super().retrieve(request, *args, **kwargs)
