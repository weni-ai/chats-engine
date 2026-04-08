from django.db.models import Avg, Q
from django.utils import timezone as django_timezone
from pendulum.parser import parse as pendulum_parse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.accounts.authentication.drf.authorization import ProjectAdminAuthentication
from chats.apps.accounts.permissions import IsExternalProject
from chats.apps.api.v1.external.throttling import (
    ExternalHourRateThrottle,
    ExternalMinuteRateThrottle,
    ExternalSecondRateThrottle,
)
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room


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
          end_date    YYYY-MM-DD  End of period (23:59:59 in project timezone). Default: now.
          sector      UUID        Filter by sector (repeatable).
          queue       UUID        Filter by queue (repeatable).
          tag         UUID        Filter by tag (repeatable).
          agent       email       Filter by agent email.
        """
        project = self.get_object()
        tz = project.timezone

        now = django_timezone.now().astimezone(tz)

        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        start_dt = (
            pendulum_parse(start_date_str, tzinfo=tz)
            if start_date_str
            else now.replace(hour=0, minute=0, second=0, microsecond=0)
        )
        end_dt = (
            pendulum_parse(end_date_str + " 23:59:59", tzinfo=tz)
            if end_date_str
            else now
        )

        rooms_filter = (
            Q(queue__sector__project=project)
            & Q(is_active=False)
            & Q(ended_at__gte=start_dt)
            & Q(ended_at__lte=end_dt)
        )

        sectors = request.query_params.getlist("sector")
        if sectors:
            rooms_filter &= Q(queue__sector__uuid__in=sectors)

        queues = request.query_params.getlist("queue")
        if queues:
            rooms_filter &= Q(queue__uuid__in=queues)

        tags = request.query_params.getlist("tag")
        if tags:
            rooms_filter &= Q(tags__uuid__in=tags)

        agent = request.query_params.get("agent")
        if agent:
            rooms_filter &= Q(user=agent)

        rooms_qs = Room.objects.filter(rooms_filter)

        avg_waiting = rooms_qs.aggregate(avg=Avg("metric__waiting_time"))["avg"]
        avg_first_response = rooms_qs.aggregate(
            avg=Avg("metric__first_response_time")
        )["avg"]
        avg_message_response = (
            rooms_qs.filter(metric__isnull=False, metric__message_response_time__gt=0)
            .aggregate(avg=Avg("metric__message_response_time"))["avg"]
        )
        avg_conversation = (
            rooms_qs.filter(first_user_assigned_at__isnull=False)
            .aggregate(avg=Avg("metric__interaction_time"))["avg"]
        )

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
