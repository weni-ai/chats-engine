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

from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.service import AgentsService


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
        url_name="csat_score_by_agents",
        url_path="csat-score-by-agents",
    )
    def csat_score_by_agents(self, request, *args, **kwargs):
        """CSAT score by agents for the project"""
        project = self.get_object()
        params = request.query_params.dict()
        filters = Filters(
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            agent=params.get("agent"),
            sector=request.query_params.getlist("sectors", []),
            tag=params.get("tags"),
            tags=request.query_params.getlist("tags", []),
            queue=params.get("queue"),
            queues=request.query_params.getlist("queues", []),
            user_request=params.get("user_request", ""),
            is_weni_admin=should_exclude_admin_domains(params.get("user_request", "")),
            ordering=params.get("ordering"),
        )

        agents_service = AgentsService()
        general_csat_metrics, agents_csat_metrics = (
            agents_service.get_agents_csat_score(filters, project)
        )

        agents_csat_metrics = agents_csat_metrics.order_by("-avg_rating")
        paginator = CustomCursorPagination()
        paginator.ordering = "-avg_rating"

        # Apply pagination
        paginated_agents = paginator.paginate_queryset(
            agents_csat_metrics, request, view=self
        )

        if paginated_agents is not None:
            # If pagination is applied, return paginated response
            serializer = DashboardCSATScoreByAgentsSerializer(
                paginated_agents, many=True
            )
            paginated_response = paginator.get_paginated_response(serializer.data)

            return Response(
                {
                    "general": DashboardCSATScoreGeneralSerializer(
                        general_csat_metrics
                    ).data,
                    **paginated_response.data,
                },
                status.HTTP_200_OK,
            )
        else:
            # If no pagination, return simple response
            serializer = DashboardCSATScoreByAgentsSerializer(
                agents_csat_metrics, many=True
            )
            return Response(
                {
                    "general": DashboardCSATScoreGeneralSerializer(
                        general_csat_metrics
                    ).data,
                    "results": serializer.data,
                },
                status.HTTP_200_OK,
            )
