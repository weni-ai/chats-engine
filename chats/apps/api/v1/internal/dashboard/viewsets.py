from django.db.models import Count, Exists, OuterRef, Q, Subquery

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.api.v1.dashboard.dto import (
    get_admin_domains_exclude_filter,
    should_exclude_admin_domains,
)
from chats.apps.api.v1.internal.dashboard.serializers import (
    DashboardAgentsSerializer,
    DashboardCustomAgentStatusSerializer,
    DashboardCSATScoreByAgentsSerializer,
    DashboardCSATScoreGeneralSerializer,
    DashboardCSATRatingsSerializer,
    DashboardCustomStatusSerializer,
)
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import CustomStatus
from chats.apps.accounts.models import User
from chats.apps.api.pagination import CustomCursorPagination

from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.service import AgentsService, CSATService
from chats.apps.core.filters import get_filters_from_query_params


def _build_status_filter(status_list):
    """
    Monta Q para filtrar agentes por status.
    Valores aceitos: 'online', 'custom_breaks', 'offline'.
    Queryset precisa já ter os annotations 'status' e 'has_active_custom_status'.
    """
    if not status_list:
        return None
    values = set()
    for s in status_list:
        for part in s.split(","):
            part = part.lower().strip()
            if part:
                values.add(part)
    if not values:
        return None
    q = Q()
    if "online" in values:
        q |= Q(status="ONLINE")
    if "custom_breaks" in values:
        q |= Q(status="OFFLINE", has_active_custom_status=True)
    if "offline" in values:
        q |= Q(status="OFFLINE", has_active_custom_status=False)
    return q if q else None


class InternalDashboardViewset(viewsets.GenericViewSet):
    swagger_tag = "Dashboard"
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

        print(f"🔥 DEBUG VIEWSET: params completos = {params}")
        print(f"🔥 DEBUG VIEWSET: agent param = '{params.get('agent')}'")
        print(f"🔥 DEBUG VIEWSET: request.query_params = {dict(request.query_params)}")

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

        print(f"🔥 DEBUG VIEWSET: filters.agent = '{filters.agent}'")

        agents_service = AgentsService()
        agents_data = agents_service.get_agents_data(filters, project)

        status_filter = _build_status_filter(
            request.query_params.getlist("status")
        )
        if status_filter is not None:
            agents_data = agents_data.filter(status_filter)

        custom_status_names = request.query_params.getlist("custom_status")
        if custom_status_names:
            agents_data = agents_data.filter(
                user_custom_status__status_type__name__in=custom_status_names,
                user_custom_status__is_active=True,
                user_custom_status__project=project,
            )

        agents = DashboardAgentsSerializer(agents_data, many=True)

        return Response({"results": agents.data}, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        url_name="agents_totals",
        url_path="agents_totals",
    )
    def agents_totals(self, request, *args, **kwargs):
        """
        Endpoint de contagem de agentes por status.
        GET /v1/internal/dashboard/{project_uuid}/agents_totals/
        Query params opcionais:
            - status (lista: 'custom_breaks', 'online', 'offline') — quando vazio traz todos
            - sector, queue, agent, user_request — mesmos filtros gerais do endpoint de agents
        Retorna: {"online": N, "custom_breaks": N, "offline": N}
        """
        project = self.get_object()

        agents_filters = Q(
            project_permissions__project=project, is_active=True
        )

        queue = request.query_params.get("queue")
        sectors = request.query_params.getlist("sector")
        agent = request.query_params.get("agent")

        if queue:
            agents_filters &= (
                Q(project_permissions__queue_authorizations__queue=queue)
                | Q(rooms__queue=queue)
            )
        elif sectors:
            agents_filters &= (
                Q(project_permissions__sector_authorizations__sector__in=sectors)
                | Q(rooms__queue__sector__in=sectors)
                | Q(project_permissions__queue_authorizations__queue__sector__in=sectors)
            )

        is_weni_admin = should_exclude_admin_domains(
            request.query_params.get("user_request", "")
        )

        agents_query = User.objects.filter(agents_filters).distinct()

        if not is_weni_admin:
            agents_query = agents_query.exclude(get_admin_domains_exclude_filter())

        if agent:
            agents_query = agents_query.filter(email=agent)

        project_permission_subquery = ProjectPermission.objects.filter(
            project_id=project,
            user_id=OuterRef("email"),
        ).values("status")[:1]

        has_active_custom_status_sub = Exists(
            CustomStatus.objects.filter(
                user=OuterRef("email"),
                status_type__project=project,
                is_active=True,
            ).exclude(status_type__name__iexact="in-service")
        )

        agents_query = agents_query.annotate(
            perm_status=Subquery(project_permission_subquery),
            has_active_custom_status=has_active_custom_status_sub,
        )

        status_param = request.query_params.getlist("status")
        requested = set()
        for s in status_param:
            for part in s.split(","):
                part = part.lower().strip()
                if part:
                    requested.add(part)
        if not requested:
            requested = {"online", "custom_breaks", "offline"}

        aggregate_kwargs = {}
        if "online" in requested:
            aggregate_kwargs["online"] = Count(
                "email", distinct=True, filter=Q(perm_status="ONLINE"),
            )
        if "custom_breaks" in requested:
            aggregate_kwargs["custom_breaks"] = Count(
                "email", distinct=True,
                filter=Q(perm_status="OFFLINE", has_active_custom_status=True),
            )
        if "offline" in requested:
            aggregate_kwargs["offline"] = Count(
                "email", distinct=True,
                filter=Q(perm_status="OFFLINE", has_active_custom_status=False),
            )

        custom_status_names = request.query_params.getlist("custom_status")
        if custom_status_names:
            agents_query = agents_query.filter(
                user_custom_status__status_type__name__in=custom_status_names,
                user_custom_status__is_active=True,
                user_custom_status__project=project,
            )

        totals = agents_query.aggregate(**aggregate_kwargs)

        return Response(totals, status.HTTP_200_OK)

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
        agents_data = agents_service.get_agents_custom_status_and_rooms(
            filters, project
        )
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

    @action(
        detail=True,
        methods=["GET"],
        url_name="custom_status_by_agent",
        url_path="custom-status-by-agent",
    )
    def custom_status_by_agent(self, request, *args, **kwargs):
        """Custom status metrics for the agent"""
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

        page = self.paginate_queryset(agents_data)
        if page is not None:
            serializer = DashboardCustomStatusSerializer(
                page, many=True, context={"project": project}
            )
            return self.get_paginated_response(serializer.data)

        serializer = DashboardCustomStatusSerializer(
            agents_data, many=True, context={"project": project}
        )

        return Response({"results": serializer.data}, status.HTTP_200_OK)
