from zoneinfo import ZoneInfo

from django.contrib.postgres.aggregates import JSONBAgg
from django.contrib.postgres.fields import JSONField
from django.db.models import (
    QuerySet,
    Avg,
    Case,
    Count,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Extract, JSONObject
from django.utils import timezone
from datetime import datetime
import pytz
import re
from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.dto import get_admin_domains_exclude_filter
from chats.apps.projects.models import ProjectPermission
from chats.apps.projects.models.models import CustomStatus, Project
from chats.apps.rooms.models import Room

from chats.apps.api.v1.internal.dashboard.dto import CSATScoreGeneral, Filters


class AgentRepository:
    def __init__(self):
        self.model = User.objects

    def get_agents_data(self, filters: Filters, project):
        tz = project.timezone
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        rooms_filter = {}
        closed_rooms = {}
        opened_rooms = {}

        agents_filters = Q(project_permissions__project=project) & Q(is_active=True)

        if filters.queue:
            rooms_filter["rooms__queue"] = filters.queue
            agents_filters &= Q(
                project_permissions__queue_authorizations__queue=filters.queue
            ) | Q(rooms__queue=filters.queue)

        elif filters.sector:
            rooms_filter["rooms__queue__sector__in"] = filters.sector
            agents_filters &= Q(
                project_permissions__sector_authorizations__sector__in=filters.sector
            ) | Q(rooms__queue__sector__in=filters.sector)
        else:
            rooms_filter["rooms__queue__sector__project"] = project
        if filters.tag:
            rooms_filter["rooms__tags__in"] = filters.tag.split(",")
        if filters.start_date and filters.end_date:
            start_time = filters.start_date
            end_time = filters.end_date
            opened_rooms["rooms__is_active"] = True
            opened_rooms["rooms__created_on__lte"] = end_time

            closed_rooms["rooms__ended_at__range"] = [start_time, end_time]
            closed_rooms["rooms__is_active"] = False
        else:
            closed_rooms["rooms__ended_at__gte"] = initial_datetime
            opened_rooms["rooms__is_active"] = True
            closed_rooms["rooms__is_active"] = False

        if filters.agent:
            rooms_filter["rooms__user"] = filters.agent

        project_permission_subquery = ProjectPermission.objects.filter(
            project_id=project,
            user_id=OuterRef("email"),
        ).values("status")[:1]

        agents_query = self.model
        if not filters.is_weni_admin:
            agents_query = agents_query.exclude(get_admin_domains_exclude_filter())

        if filters.agent:
            agents_query = agents_query.filter(email=filters.agent)

        custom_status_subquery = Subquery(
            CustomStatus.objects.filter(
                user=OuterRef("email"),
                status_type__project=project,
            )
            .values("user")
            .annotate(
                aggregated=JSONBAgg(
                    JSONObject(
                        status_type=F("status_type__name"),
                        break_time=F("break_time"),
                        is_active=F("is_active"),
                        created_on=F("created_on"),
                    )
                )
            )
            .values("aggregated"),
            output_field=JSONField(),
        )

        in_service_time_subquery = (
            CustomStatus.objects.filter(
                user=OuterRef("email"),
                status_type__project=project,
                status_type__name="In-Service",
            )
            .annotate(
                time_contribution=Case(
                    When(
                        is_active=True,
                        user__project_permissions__status="ONLINE",
                        user__project_permissions__project=project,
                        then=Extract(timezone.now() - F("created_on"), "epoch"),
                    ),
                    When(is_active=False, then=F("break_time")),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
            .values("user")
            .annotate(total=Sum("time_contribution"))
            .values("total")
        )

        agents_query = (
            agents_query.filter(agents_filters)
            .annotate(
                status=Subquery(project_permission_subquery),
                closed=Count(
                    "rooms__uuid",
                    distinct=True,
                    filter=Q(**closed_rooms, **rooms_filter),
                ),
                opened=Count(
                    "rooms__uuid",
                    distinct=True,
                    filter=Q(**opened_rooms, **rooms_filter),
                ),
                avg_first_response_time=Avg(
                    "rooms__metric__first_response_time",
                    filter=Q(**closed_rooms, **rooms_filter)
                    & Q(rooms__metric__first_response_time__gt=0),
                ),
                avg_message_response_time=Avg(
                    "rooms__metric__message_response_time",
                    filter=Q(**closed_rooms, **rooms_filter)
                    & Q(rooms__metric__message_response_time__gt=0),
                ),
                avg_interaction_time=Avg(
                    "rooms__metric__interaction_time",
                    filter=Q(**closed_rooms, **rooms_filter)
                    & Q(rooms__metric__interaction_time__gt=0),
                ),
                custom_status=custom_status_subquery,
                time_in_service_order=Coalesce(
                    Subquery(in_service_time_subquery, output_field=IntegerField()),
                    Value(0),
                ),
            )
            .distinct()
        )

        if filters.ordering:
            if "time_in_service" in filters.ordering:
                ordering_field = filters.ordering.replace(
                    "time_in_service", "time_in_service_order"
                )
                agents_query = agents_query.order_by(ordering_field)
            else:
                agents_query = agents_query.order_by(filters.ordering)

        agents_query = agents_query.values(
            "first_name",
            "last_name",
            "email",
            "status",
            "closed",
            "opened",
            "avg_first_response_time",
            "avg_message_response_time",
            "avg_interaction_time",
            "custom_status",
        )

        return agents_query

    def get_agents_custom_status(self, filters: Filters, project):
        tz = project.timezone
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )

        rooms_filter = {}
        closed_rooms = {}
        opened_rooms = {}
        agents_filter = {}

        if filters.queue and filters.sector:
            rooms_filter["rooms__queue"] = filters.queue
            rooms_filter["rooms__queue__sector__in"] = filters.sector
            agents_filter["project_permissions__queue_authorizations__queue"] = (
                filters.queue
            )
            agents_filter[
                "project_permissions__queue_authorizations__queue__sector__in"
            ] = filters.sector
        elif filters.queue:
            rooms_filter["rooms__queue"] = filters.queue
            agents_filter["project_permissions__queue_authorizations__queue"] = (
                filters.queue
            )
        elif filters.sector:
            rooms_filter["rooms__queue__sector__in"] = filters.sector
            agents_filter[
                "project_permissions__queue_authorizations__queue__sector__in"
            ] = filters.sector
        else:
            rooms_filter["rooms__queue__sector__project"] = project

        if filters.tag:
            rooms_filter["rooms__tags__in"] = filters.tag.split(",")

        if filters.start_date and filters.end_date:
            start_time = filters.start_date
            end_time = filters.end_date
            rooms_filter["rooms__created_on__range"] = [start_time, end_time]
            rooms_filter["rooms__is_active"] = False
            closed_rooms["rooms__ended_at__range"] = [start_time, end_time]
        else:
            closed_rooms["rooms__ended_at__gte"] = initial_datetime
            opened_rooms["rooms__is_active"] = True
            closed_rooms["rooms__is_active"] = False

        if filters.agent:
            rooms_filter["rooms__user"] = filters.agent

        project_permission_queryset = ProjectPermission.objects.filter(
            project_id=project,
            user_id=OuterRef("email"),
        ).values("status")[:1]

        custom_status_subquery = Subquery(
            CustomStatus.objects.filter(
                user=OuterRef("email"),
                status_type__project=project,
            )
            .values("user")
            .annotate(
                aggregated=JSONBAgg(
                    JSONObject(
                        status_type=F("status_type__name"),
                        break_time=F("break_time"),
                        is_active=F("is_active"),
                        created_on=F("created_on"),
                    )
                )
            )
            .values("aggregated"),
            output_field=JSONField(),
        )

        agents_query = self.model.all()

        if not filters.is_weni_admin:
            agents_query = agents_query.exclude(get_admin_domains_exclude_filter())
        if filters.agent:
            agents_query = agents_query.filter(email=filters.agent)

        if agents_filter:
            agents_query = agents_query.filter(**agents_filter).distinct()

        agents_query = (
            agents_query.filter(project_permissions__project=project, is_active=True)
            .annotate(
                status=Subquery(project_permission_queryset),
                closed=Count(
                    "rooms__uuid",
                    distinct=True,
                    filter=Q(**closed_rooms, **rooms_filter),
                ),
                opened=Count(
                    "rooms__uuid",
                    distinct=True,
                    filter=Q(**opened_rooms, **rooms_filter),
                ),
                custom_status=custom_status_subquery,
            )
            .distinct()
        )

        if filters.ordering:
            agents_query = agents_query.order_by(filters.ordering)

        agents_query = agents_query.values(
            "first_name",
            "last_name",
            "email",
            "status",
            "closed",
            "opened",
            "custom_status",
        )

        return agents_query

    def _parse_date_with_timezone(
        self, date_str: str, project_timezone: str, is_end_date: bool = False
    ) -> datetime:
        """
        Parse date string with different formats and handle timezone conversion.

        Args:
            date_str: Date string in various formats (YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, etc.)
            project_timezone: Project's timezone key
            is_end_date: If True, sets time to 23:59:59, otherwise 00:00:00

        Returns:
            datetime object with project timezone
        """
        if not date_str:
            return None

        tz = pytz.timezone(project_timezone)

        # Check if it's just a date (YYYY-MM-DD)
        date_only_pattern = r"^\d{4}-\d{2}-\d{2}$"
        if re.match(date_only_pattern, date_str):
            time_str = " 23:59:59" if is_end_date else " 00:00:00"
            naive_dt = datetime.strptime(date_str + time_str, "%Y-%m-%d %H:%M:%S")
            return tz.localize(naive_dt)

        # Try to parse as ISO datetime format with timezone
        try:
            # First try to parse as timezone-aware datetime
            if (
                "+" in date_str
                or date_str.endswith("Z")
                or re.search(r"[+-]\d{4}$", date_str)
            ):
                # Handle timezone-aware formats
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                # Convert to project timezone
                return dt.astimezone(tz)
        except ValueError:
            pass

        # Try to parse as naive datetime formats
        try:
            datetime_formats = [
                "%Y-%m-%dT%H:%M:%S",  # 2025-01-01T00:00:00
                "%Y-%m-%dT%H:%M:%S.%f",  # 2025-01-01T00:00:00.000000
                "%Y-%m-%d %H:%M:%S",  # 2025-01-01 00:00:00
                "%Y-%m-%d %H:%M:%S.%f",  # 2025-01-01 00:00:00.000000
            ]

            naive_dt = None
            for fmt in datetime_formats:
                try:
                    naive_dt = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue

            if naive_dt is not None:
                # Localize with project timezone
                return tz.localize(naive_dt)

        except ValueError:
            pass

        time_str = " 23:59:59" if is_end_date else " 00:00:00"
        naive_dt = datetime.strptime(date_str + time_str, "%Y-%m-%d %H:%M:%S")
        return tz.localize(naive_dt)

    def _get_converted_dates(self, filters: Filters, project: Project) -> dict:
        project_timezone = project.timezone if project.timezone else "UTC"

        if isinstance(project_timezone, ZoneInfo):
            project_timezone = project_timezone.key

        start_date = None
        end_date = None

        if filters.start_date:
            start_date = self._parse_date_with_timezone(
                filters.start_date, project_timezone, is_end_date=False
            )

        if filters.end_date:
            end_date = self._parse_date_with_timezone(
                filters.end_date, project_timezone, is_end_date=True
            )

        return start_date, end_date

    def _get_csat_general(self, filters: Filters, project: Project) -> CSATScoreGeneral:
        rooms_query = {
            "is_active": False,
        }
        start_date, end_date = self._get_converted_dates(filters, project)

        if filters.start_date:
            rooms_query["ended_at__gte"] = start_date

        if filters.end_date:
            rooms_query["ended_at__lte"] = end_date

        if filters.sector:
            rooms_query["queue__sector__in"] = filters.sector

        if filters.queue:
            rooms_query["queue"] = filters.queue

        if filters.tag:
            rooms_query["tags__in"] = filters.tag.split(",")

        return CSATScoreGeneral(
            rooms=Room.objects.filter(**rooms_query).count(),
            reviews=Room.objects.filter(
                csat_survey__isnull=False,
                csat_survey__rating__isnull=False,
                **rooms_query
            ).count(),
            avg_rating=Room.objects.filter(
                csat_survey__isnull=False,
                csat_survey__rating__isnull=False,
                **rooms_query
            ).aggregate(avg_rating=Avg("csat_survey__rating"))["avg_rating"],
        )

    def _get_csat_agents(self, filters: Filters, project: Project) -> QuerySet[User]:
        agents = User.objects.filter(project_permissions__project=project)

        if not filters.is_weni_admin:
            agents = agents.exclude(get_admin_domains_exclude_filter())

        if filters.sector:
            agents = agents.filter(
                project_permissions__sector_authorizations__sector__in=filters.sector
            )

        if filters.queue:
            agents = agents.filter(
                project_permissions__queue_authorizations__queue=filters.queue
            )

        if filters.agent:
            agents = agents.filter(email=filters.agent)

        return agents

    def _get_csat_rooms_query(self, filters: Filters, project: Project) -> dict:
        rooms_query = {
            "rooms__is_active": False,
        }
        start_date, end_date = self._get_converted_dates(filters, project)

        if filters.start_date:
            rooms_query["rooms__ended_at__gte"] = start_date

        if filters.end_date:
            rooms_query["rooms__ended_at__lte"] = end_date

        if filters.sector:
            rooms_query["rooms__queue__sector__in"] = filters.sector

        if filters.queue:
            rooms_query["rooms__queue"] = filters.queue

        if filters.tag:
            rooms_query["rooms__tags__in"] = filters.tag.split(",")

        return rooms_query

    def get_agents_csat_score(self, filters: Filters, project: Project) -> tuple:
        agents = self._get_csat_agents(filters, project)
        rooms_query = self._get_csat_rooms_query(filters, project)

        csat_reviews_query = rooms_query.copy()
        csat_reviews_query["rooms__csat_survey__isnull"] = False
        csat_reviews_query["rooms__csat_survey__rating__isnull"] = False

        agents = agents.annotate(
            rooms_count=Count(
                "rooms__uuid",
                distinct=True,
                filter=Q(**rooms_query),
            ),
            reviews=Count(
                "rooms__csat_survey__rating",
                distinct=True,
                filter=Q(**csat_reviews_query),
            ),
            avg_rating=Avg(
                "rooms__csat_survey__rating",
                filter=Q(**csat_reviews_query),
            ),
        ).order_by("-avg_rating")

        return self._get_csat_general(filters, project), agents.values(
            "email", "first_name", "last_name", "rooms_count", "reviews", "avg_rating"
        )
