from datetime import date

from django.db.models import OuterRef, Subquery
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status as http_status, viewsets
from rest_framework.response import Response

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.api.v1.external.agents.calculator import build_agent_log_maps
from chats.apps.api.v1.external.agents.filters import AgentFlowFilter
from chats.apps.api.v1.external.agents.serializers import (
    AgentFlowSerializer,
    AgentStatusSerializer,
)
from chats.apps.api.v1.external.throttling import (
    ExternalHourRateThrottle,
    ExternalMinuteRateThrottle,
    ExternalSecondRateThrottle,
)
from chats.apps.projects.models import ProjectPermission
from chats.apps.projects.models.models import CustomStatus


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
        return super().get_queryset().filter(project=self.request.auth.project)

    def list(self, request, *args, **kwargs):
        """List all agents (users with permissions) in the authenticated project."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve details of a specific agent by UUID."""
        return super().retrieve(request, *args, **kwargs)


class ExternalAgentsStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lists agents with real-time status, custom status (pause reason),
    last_seen timestamp, last status change and time in current status.

    Requires project admin authentication via Bearer token.
    Rate limited: 20/sec, 600/min, 30k/hour.
    """

    swagger_tag = "Integrations"
    model = ProjectPermission
    queryset = ProjectPermission.objects.all()
    serializer_class = AgentStatusSerializer
    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]
    throttle_classes = [
        ExternalSecondRateThrottle,
        ExternalMinuteRateThrottle,
        ExternalHourRateThrottle,
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AgentFlowFilter
    authentication_classes = [ProjectAdminAuthentication]

    def get_queryset(self):
        project_uuid = self.request.auth.project

        custom_status_qs = CustomStatus.objects.filter(
            user=OuterRef("user__email"),
            status_type__project=OuterRef("project"),
            is_active=True,
        ).exclude(status_type__name__iexact="in-service")

        return (
            ProjectPermission.objects.filter(
                project__uuid=project_uuid,
                role__in=[
                    ProjectPermission.ROLE_ADMIN,
                    ProjectPermission.ROLE_ATTENDANT,
                ],
            )
            .select_related("user")
            .annotate(
                _custom_status_name=Subquery(
                    custom_status_qs.values("status_type__name")[:1]
                ),
                _custom_status_since=Subquery(
                    custom_status_qs.values("created_on")[:1]
                ),
            )
        )

    def _parse_date_param(self, param_name):
        raw = self.request.query_params.get(param_name)
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except (ValueError, TypeError):
            return None

    def list(self, request, *args, **kwargs):
        """List all agents with their current status and monitoring data."""
        queryset = self.filter_queryset(self.get_queryset())

        start_date = self._parse_date_param("start_date")
        end_date = self._parse_date_param("end_date")

        status_log_map, online_time_map = build_agent_log_maps(
            request.auth.project, start_date, end_date
        )

        page = self.paginate_queryset(queryset)
        data = page if page is not None else queryset

        serializer = self.get_serializer(
            data,
            many=True,
            context={
                "request": request,
                "status_log_map": status_log_map,
                "online_time_map": online_time_map,
            },
        )

        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data, status=http_status.HTTP_200_OK)
