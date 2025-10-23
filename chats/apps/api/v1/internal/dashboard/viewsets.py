from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.api.v1.dashboard.dto import should_exclude_admin_domains
from chats.apps.api.v1.internal.dashboard.serializers import (
    DashboardAgentsSerializer,
    DashboardCustomAgentStatusSerializer,
    DashboardCSATScoreByAgentsSerializer,
    DashboardCSATScoreGeneralSerializer,
)
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.projects.models import Project
from chats.apps.api.pagination import CustomCursorPagination

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
            sector=request.query_params.getlist("sector"),
            tag=params.get("tags"),
            queue=params.get("queue"),
            user_request=params.get("user_request", ""),
            is_weni_admin=should_exclude_admin_domains(params.get("user_request", "")),
            ordering=params.get("ordering"),
        )

        agents_service = AgentsService()
        agents_data = agents_service.get_agents_data(filters, project)
        agents = DashboardAgentsSerializer(agents_data, many=True)

        return Response({"results": agents.data}, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        url_name="custom_status_agent",
    )
    def custom_status_agent(self, request, *args, **kwargs):
        """Agent metrics for the custom status"""
        project = self.get_object()
        params = request.query_params.dict()
        filters = Filters(
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            agent=params.get("agent"),
            sector=request.query_params.getlist("sector"),
            tag=params.get("tags"),
            queue=params.get("queue"),
            user_request=params.get("user_request", ""),
            is_weni_admin=should_exclude_admin_domains(params.get("user_request", "")),
            ordering=params.get("ordering"),
        )

        agents_service = AgentsService()
        agents_data = agents_service.get_agents_custom_status(filters, project)
        agents = DashboardCustomAgentStatusSerializer(
            agents_data, many=True, context={"project": project}
        )

        return Response({"results": agents.data}, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        url_name="csat_score",
    )
    def csat_score_by_agents(self, request, *args, **kwargs):
        """CSAT score by agents for the project"""
        project = self.get_object()
        params = request.query_params.dict()
        filters = Filters(
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            agent=params.get("agent"),
            sector=request.query_params.getlist("sector"),
            tag=params.get("tags"),
            queue=params.get("queue"),
            user_request=params.get("user_request", ""),
            is_weni_admin=should_exclude_admin_domains(params.get("user_request", "")),
            ordering=params.get("ordering"),
        )

        agents_service = AgentsService()
        general_csat_metrics, agents_csat_metrics = (
            agents_service.get_agents_csat_score(filters, project)
        )

        self.ordering = "-avg_rating"
        agents_csat_metrics_page = CustomCursorPagination().paginate_queryset(
            agents_csat_metrics, request, view=self
        )

        return Response(
            {
                "general": DashboardCSATScoreGeneralSerializer(
                    general_csat_metrics
                ).data,
                "results": DashboardCSATScoreByAgentsSerializer(
                    agents_csat_metrics_page.object_list, many=True
                ).data,
            },
            status.HTTP_200_OK,
        )
