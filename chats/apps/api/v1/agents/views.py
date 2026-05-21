from django.conf import settings
from django.db import transaction
from django.db.models import (
    Case,
    Exists,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
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
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

from chats.apps.api.v1.agents.filters import AllAgentsFilter
from chats.apps.api.v1.agents.serializers import (
    AgentQueuePermissionsSerializer,
    AllAgentsSerializer,
    UpdateQueuePermissionsSerializer,
)
from chats.apps.api.v1.permissions import AnySectorManagerPermission
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import CustomStatus
from chats.apps.queues.models import Queue, QueueAuthorization


def _check_agents_management_feature(project):
    """Raises 403 if the agents management feature is not enabled for the project."""
    if not is_feature_active_for_attributes(
        settings.AGENTS_MANAGEMENT_FEATURE_FLAG_KEY,
        {"projectUUID": str(project.uuid)},
    ):
        raise PermissionDenied("Feature not available for this project.")


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
    Returns a Case/When expression producing the ordering key for the
    AllAgentsView queryset. Requires the `active_pause_name` annotation
    (Subquery) to already be present on the queryset:
      0 = ONLINE without any active pause
      1 = active custom pause (any status)
      2 = OFFLINE
    """
    return Case(
        When(active_pause_name__isnull=False, then=Value(1)),
        When(status=ProjectPermission.STATUS_OFFLINE, then=Value(2)),
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
    Filters: status (online, offline, or custom pause name), agent (email), sector, queue.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AllAgentsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AllAgentsFilter
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        project = get_object_or_404(Project, uuid=self.kwargs["project_uuid"])
        _check_agents_management_feature(project)
        _get_manager_permission(self.request, project)

        active_pause_name = (
            CustomStatus.objects.filter(
                user_id=OuterRef("user_id"),
                project=OuterRef("project"),
                is_active=True,
            )
            .exclude(status_type__name__iexact="in-service")
            .values("status_type__name")[:1]
        )

        active_queue_auths = QueueAuthorization.objects.filter(
            queue__is_deleted=False,
            queue__sector__is_deleted=False,
        ).select_related("queue__sector")

        has_active_queue_auth = QueueAuthorization.objects.filter(
            permission=OuterRef("pk"),
            queue__is_deleted=False,
            queue__sector__is_deleted=False,
        )

        return (
            ProjectPermission.objects.filter(
                project=project,
                is_deleted=False,
            )
            .filter(
                Q(role=ProjectPermission.ROLE_ATTENDANT) | Exists(has_active_queue_auth)
            )
            .select_related("user")
            .prefetch_related(
                Prefetch("queue_authorizations", queryset=active_queue_auths),
            )
            .annotate(active_pause_name=Subquery(active_pause_name))
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
        _check_agents_management_feature(project)
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

    permission_classes = [IsAuthenticated, AnySectorManagerPermission]

    def post(self, request):
        serializer = UpdateQueuePermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = get_object_or_404(Project, uuid=data["project"])
        _check_agents_management_feature(project)

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


# ---------------------------------------------------------------------------
# GET /v1/project/{project_uuid}/sectors/queues/?sectors=uuid1,uuid2
# ---------------------------------------------------------------------------


class SectorsQueuesView(APIView):
    """
    Returns queues grouped by sector for the given project.

    Query params:
        sectors — comma-separated list of sector UUIDs (optional)
        limit   — page size (LimitOffsetPagination)
        offset  — page offset (LimitOffsetPagination)

    When `sectors` is omitted, all sectors of the project are returned.
    Deleted sectors and queues are ignored.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination

    @property
    def paginator(self):
        if not hasattr(self, "_paginator"):
            self._paginator = self.pagination_class()
        return self._paginator

    def get(self, request, project_uuid):
        project = get_object_or_404(Project, uuid=project_uuid)
        _check_agents_management_feature(project)
        _get_manager_permission(request, project)

        raw = request.query_params.get("sectors", "").strip()
        sector_uuids = [token for token in (s.strip() for s in raw.split(",")) if token]

        sectors_qs = project.sectors.filter(is_deleted=False)
        if sector_uuids:
            sectors_qs = sectors_qs.filter(uuid__in=sector_uuids)

        sectors_qs = sectors_qs.prefetch_related(
            Prefetch(
                "queues",
                queryset=Queue.objects.filter(is_deleted=False).order_by("name"),
            )
        ).order_by("name")

        page = self.paginator.paginate_queryset(sectors_qs, request, view=self)

        data = [
            {
                "uuid": str(sector.uuid),
                "name": sector.name,
                "queues": [
                    {"uuid": str(queue.uuid), "name": queue.name}
                    for queue in sector.queues.all()
                ],
            }
            for sector in page
        ]

        return self.paginator.get_paginated_response(data)
