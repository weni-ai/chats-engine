from django.db import transaction
from django.db.models import (
    Case,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Prefetch,
    Value,
    When,
)
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.apps.api.v1.agents.filters import AllAgentsFilter
from chats.apps.api.v1.agents.serializers import (
    AgentQueuePermissionsSerializer,
    AllAgentsSerializer,
    UpdateQueuePermissionsSerializer,
)
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import CustomStatus
from chats.apps.queues.models import Queue, QueueAuthorization


def _get_manager_permission(request, project):
    """Returns the ProjectPermission for the requesting user, raising 403 if not a manager."""
    perm = get_object_or_404(
        ProjectPermission,
        project=project,
        user=request.user,
        is_deleted=False,
    )
    if not perm.is_manager(any_sector=True):
        raise PermissionDenied()
    return perm


def _status_order_annotation():
    """
    Annotates a ProjectPermission queryset with a numeric ordering key:
      0 = ONLINE without any active pause
      1 = any status with an active custom pause
      2 = OFFLINE
    """
    active_pause = CustomStatus.objects.filter(
        user_id=OuterRef("user_id"),
        project=OuterRef("project"),
        is_active=True,
    ).exclude(status_type__name__iexact="in-service")

    return Case(
        When(status=ProjectPermission.STATUS_OFFLINE, then=Value(2)),
        When(Exists(active_pause), then=Value(1)),
        When(status=ProjectPermission.STATUS_ONLINE, then=Value(0)),
        default=Value(2),
        output_field=IntegerField(),
    )


# ---------------------------------------------------------------------------
# ENGAGE-7672 — GET /v1/project/{project_uuid}/all_agents
# ---------------------------------------------------------------------------


class AllAgentsView(generics.ListAPIView):
    """
    Lists all attendant agents of a project with ordering and filters.

    Ordering: ONLINE → pause (active custom status) → OFFLINE, then alphabetical.
    Filters: status, custom_status, agent (email), sector, queue.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AllAgentsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AllAgentsFilter
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        project = get_object_or_404(Project, uuid=self.kwargs["project_uuid"])
        _get_manager_permission(self.request, project)

        return (
            ProjectPermission.objects.filter(
                project=project,
                role=ProjectPermission.ROLE_ATTENDANT,
                is_deleted=False,
            )
            .select_related("user")
            .prefetch_related(
                "sector_authorizations__sector",
                "queue_authorizations__queue__sector",
            )
            .annotate(status_order=_status_order_annotation())
            .order_by("status_order", "user__first_name", "user__last_name")
        )


# ---------------------------------------------------------------------------
# ENGAGE-7558 — GET /v1/agent/queue_permissions/
# ---------------------------------------------------------------------------


class AgentQueuePermissionsView(APIView):
    """
    Returns the queue permissions modal data for a given agent.

    Lists all sectors of the project with all their queues, flagging
    agent_in_queue=True for queues the agent belongs to.
    Also returns the agent's chats_limit configuration.

    Query params:
        agent   — email of the agent
        project — UUID of the project
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        agent_email = request.query_params.get("agent")
        project_uuid = request.query_params.get("project")

        if not agent_email or not project_uuid:
            return Response(
                {"detail": "Both 'agent' and 'project' query params are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project = get_object_or_404(Project, uuid=project_uuid)
        _get_manager_permission(request, project)

        agent_permission = get_object_or_404(
            ProjectPermission,
            project=project,
            user__email=agent_email,
            is_deleted=False,
        )

        sectors = project.sectors.filter(is_deleted=False).prefetch_related(
            Prefetch(
                "queues",
                queryset=Queue.objects.filter(is_deleted=False),
            )
        )

        data = AgentQueuePermissionsSerializer(
            {"permission": agent_permission, "sectors_data": sectors}
        ).data
        return Response(data)


# ---------------------------------------------------------------------------
# ENGAGE-7557 — POST /v1/agent/update_queue_permissions/
# ---------------------------------------------------------------------------


class UpdateQueuePermissionsView(APIView):
    """
    Saves queue permission changes for one or more agents.

    Body:
        agents      — list of agent emails
        to_add      — list of queue UUIDs to add the agents to
        to_remove   — list of queue UUIDs to remove the agents from
        chats_limit — {active: bool, total: int | null}
        project     — UUID of the project
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UpdateQueuePermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = get_object_or_404(Project, uuid=data["project"])
        _get_manager_permission(request, project)

        agent_emails = list(set(data["agents"]))  # deduplicate
        to_add = data.get("to_add", [])
        to_remove = data.get("to_remove", [])
        chats_limit = data.get("chats_limit")

        permissions = list(
            ProjectPermission.objects.filter(
                project=project,
                user__email__in=agent_emails,
                is_deleted=False,
            )
        )

        if len(permissions) != len(agent_emails):
            return Response(
                {"agents": "One or more agents were not found in this project."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queues_to_add = (
            list(Queue.objects.filter(uuid__in=to_add, sector__project=project))
            if to_add
            else []
        )
        queues_to_remove_ids = (
            list(
                Queue.objects.filter(
                    uuid__in=to_remove, sector__project=project
                ).values_list("pk", flat=True)
            )
            if to_remove
            else []
        )

        with transaction.atomic():
            for perm in permissions:
                if queues_to_remove_ids:
                    QueueAuthorization.objects.filter(
                        permission=perm, queue_id__in=queues_to_remove_ids
                    ).delete()

                for queue in queues_to_add:
                    QueueAuthorization.objects.get_or_create(
                        permission=perm,
                        queue=queue,
                        defaults={"role": QueueAuthorization.ROLE_AGENT},
                    )

                if chats_limit is not None:
                    perm.is_custom_limit_active = chats_limit["active"]
                    perm.custom_rooms_limit = chats_limit["total"]
                    perm.save(
                        update_fields=["is_custom_limit_active", "custom_rooms_limit"]
                    )

        return Response(status=status.HTTP_200_OK)
