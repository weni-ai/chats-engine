from django.db.models import Avg
from django.utils import timezone as django_timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
)
from chats.apps.accounts.permissions import IsExternalProject
from chats.apps.api.v1.external.throttling import (
    ExternalHourRateThrottle,
    ExternalMinuteRateThrottle,
    ExternalSecondRateThrottle,
)
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room

from .filters import ExternalFinishedRoomsStatusFilter


class ExternalFinishedRoomsStatusViewSet(viewsets.GenericViewSet):
    """
    External endpoint for consolidated finished-rooms status and time metrics.
    Requires a project Bearer token (ProjectPermission with admin role).
    Rate limited: 20/sec, 600/min, 30k/hour.
    """

    swagger_tag = "Integrations"
    lookup_field = "uuid"
    authentication_classes = [ProjectAdminAuthentication]
    permission_classes = [IsExternalProject]
    throttle_classes = [
        ExternalSecondRateThrottle,
        ExternalMinuteRateThrottle,
        ExternalHourRateThrottle,
    ]

    def get_queryset(self):
        return Project.objects.filter(uuid=self.request.auth.project)

    @action(detail=True, methods=["GET"], url_name="finished_rooms_status")
    def finished_rooms_status(self, request, uuid=None):
        """
        Returns the count of finished rooms and their time averages for a period.

        Query params:
          start_date  YYYY-MM-DD  Start of period (midnight in project timezone). Default: today.
          end_date    YYYY-MM-DD  End of period (23:59:59 in project timezone). Default: today.
          sector      UUID        Filter by sector (comma-separated).
          queue       UUID        Filter by queue (comma-separated).
          tag         UUID        Filter by tag (comma-separated).
          agent       email       Filter by agent email.
        """
        project = self.get_object()

        filter_data = request.query_params.copy()
        if not filter_data.get("start_date") or not filter_data.get("end_date"):
            today = (
                django_timezone.now().astimezone(project.timezone).strftime("%Y-%m-%d")
            )
            filter_data.setdefault("start_date", today)
            filter_data.setdefault("end_date", today)

        rooms_qs = ExternalFinishedRoomsStatusFilter(
            data=filter_data,
            queryset=Room.objects.filter(
                queue__sector__project=project,
                is_active=False,
            ),
            request=request,
        ).qs

        avg_waiting = rooms_qs.aggregate(avg=Avg("metric__waiting_time"))["avg"]
        avg_first_response = rooms_qs.aggregate(avg=Avg("metric__first_response_time"))[
            "avg"
        ]
        avg_message_response = rooms_qs.filter(
            metric__isnull=False, metric__message_response_time__gt=0
        ).aggregate(avg=Avg("metric__message_response_time"))["avg"]
        avg_conversation = rooms_qs.filter(
            first_user_assigned_at__isnull=False
        ).aggregate(avg=Avg("metric__interaction_time"))["avg"]

        return Response(
            {
                "finished": rooms_qs.count(),
                "average_waiting_time": round(float(avg_waiting or 0), 1),
                "average_first_response_time": round(float(avg_first_response or 0), 1),
                "average_response_time": round(float(avg_message_response or 0), 1),
                "average_conversation_duration": round(float(avg_conversation or 0), 1),
            },
            status=status.HTTP_200_OK,
        )
