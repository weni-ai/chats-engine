from django.db.models import OuterRef, Subquery
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status as http_status, viewsets
from rest_framework.response import Response

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
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
from chats.apps.projects.models.models import AgentStatusLog, CustomStatus


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

    def get_queryset(self):
        permission = self.request.auth
        if permission is None or permission.role != 1:
            return ProjectPermission.objects.none()

        project_uuid = permission.project

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

    def _build_status_log_map(self, project_uuid):
        """
        Single query to fetch today's status logs for all agents in the project.
        Returns {email: last_change_timestamp}.
        """
        today = timezone.now().date()
        logs = AgentStatusLog.objects.filter(
            project__uuid=project_uuid,
            log_date=today,
        ).values_list("agent__email", "status_changes")

        status_map = {}
        for email, changes in logs:
            if changes and isinstance(changes, list) and len(changes) > 0:
                status_map[email] = changes[-1].get("timestamp")
        return status_map

    def list(self, request, *args, **kwargs):
        """List all agents with their current status and monitoring data."""
        if not request.auth:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=http_status.HTTP_401_UNAUTHORIZED,
            )

        queryset = self.filter_queryset(self.get_queryset())
        status_log_map = self._build_status_log_map(request.auth.project)

        page = self.paginate_queryset(queryset)
        data = page if page is not None else queryset

        serializer = self.get_serializer(
            data,
            many=True,
            context={
                "request": request,
                "status_log_map": status_log_map,
            },
        )

        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data, status=http_status.HTTP_200_OK)
