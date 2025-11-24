from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.api.v1.dashboard.dto import should_exclude_admin_domains
from chats.apps.api.v1.internal.dashboard.serializers import (
    DashboardAgentsSerializer,
    DashboardCustomAgentStatusSerializer,
    DashboardCSATRatingsSerializer,
)
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.projects.models import Project

from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.service import AgentsService, CSATService
from chats.apps.core.filters import get_filters_from_query_params


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
        url_name="csat_ratings",
    )
    def csat_ratings(self, request, *args, **kwargs):
        """CSAT ratings for the project"""
        project = self.get_object()
        params = get_filters_from_query_params(request.query_params)
        filters = Filters(
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            queue=params.get("queue"),
            queues=params.get("queues"),
            sector=params.get("sector"),
            sectors=params.get("sectors"),
            tag=params.get("tag"),
            tags=params.get("tags"),
            agent=params.get("agent"),
        )

        csat_service = CSATService()
        csat_ratings = csat_service.get_csat_ratings(filters, project)

        return Response(
            {
                "csat_ratings": DashboardCSATRatingsSerializer(
                    csat_ratings.ratings, many=True
                ).data
            },
            status.HTTP_200_OK,
        )
