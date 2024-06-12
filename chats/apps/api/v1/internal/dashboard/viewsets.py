from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.api.v1.internal.dashboard.serializers import DashboardAgentsSerializer
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.projects.models import Project

from .dto import Filters
from .service import AgentsService


class InternalDashboardViewset(viewsets.GenericViewSet):
    lookup_field = "uuid"
    queryset = Project.objects.all()
    serializer_class = DashboardAgentsSerializer
    permission_classes = [permissions.IsAuthenticated, ModuleHasPermission]

    @action(
        detail=True,
        methods=["GET"],
        url_name="agent",
    )
    def agent(self, request, *args, **kwargs):
        """Agent metrics for the project or the sector"""
        project = self.get_object()
        params = request.query_params.dict()
        filters = Filters(
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            agent=params.get("agent"),
            sector=params.get("sector"),
            tag=params.get("tag"),
            queue=params.get("queue"),
            user_request=params.get("user_request", ""),
            is_weni_admin=(True if "weni.ai" in params.get("user_request") else False),
        )

        agents_service = AgentsService()
        agents_data = agents_service.get_agents_data(filters, project)
        agents = DashboardAgentsSerializer(agents_data, many=True)

        return Response({"results": agents.data}, status.HTTP_200_OK)
