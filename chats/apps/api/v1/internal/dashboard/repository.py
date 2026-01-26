from django.contrib.postgres.aggregates import JSONBAgg
from django.contrib.postgres.fields import JSONField
from django.db.models import (
    QuerySet,
    Avg,
    Case,
    Count,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, Extract, JSONObject
from django.utils import timezone
from pendulum.parser import parse as pendulum_parse

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.dto import get_admin_domains_exclude_filter
from chats.apps.api.v1.internal.dashboard.dto import (
    Filters,
    CSATScoreGeneral,
    CSATRatingCount,
    CSATRatings,
)
from chats.apps.projects.dates import parse_date_with_timezone
from chats.apps.projects.models import ProjectPermission
from chats.apps.projects.models.models import CustomStatus, Project
from chats.apps.csat.models import CSATSurvey
from chats.apps.rooms.models import Room


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
            # If filtering by sector, we need to include both sector and queue authorizations
            agents_filters &= (
                Q(project_permissions__sector_authorizations__sector__in=filters.sector)
                | Q(rooms__queue__sector__in=filters.sector)
                | Q(
                    project_permissions__queue_authorizations__queue__sector__in=filters.sector
                )
            )
        else:
            rooms_filter["rooms__queue__sector__project"] = project
        if filters.tag:
            rooms_filter["rooms__tags__in"] = filters.tag.split(",")
        if filters.start_date and filters.end_date:
            start_time = pendulum_parse(filters.start_date, tzinfo=tz)
            end_time = pendulum_parse(filters.end_date + " 23:59:59", tzinfo=tz)
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

        custom_status_start_date = (
            pendulum_parse(filters.start_date, tzinfo=tz)
            if filters.start_date
            else initial_datetime
        )
        custom_status_end_date = (
            pendulum_parse(filters.end_date + " 23:59:59", tzinfo=tz)
            if filters.end_date
            else timezone.now()
        )

        custom_status_subquery = Subquery(
            CustomStatus.objects.filter(
                user=OuterRef("email"),
                status_type__project=project,
                created_on__range=[custom_status_start_date, custom_status_end_date],
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

        has_active_custom_status_subquery = Exists(
            CustomStatus.objects.filter(
                user=OuterRef("email"),
                status_type__project=project,
                is_active=True,
            ).exclude(status_type__name__iexact="in-service")
        )

        agents_query = (
            agents_query.filter(agents_filters)
            .annotate(
                status=Subquery(project_permission_subquery),
                has_active_custom_status=has_active_custom_status_subquery,
                status_order=Case(
                    When(Q(status='OFFLINE') & Q(has_active_custom_status=False), then=Value(1)),
                    When(has_active_custom_status=True, then=Value(2)),
                    When(Q(status='ONLINE') & Q(has_active_custom_status=False), then=Value(3)),
                    default=Value(2),
                    output_field=IntegerField(),
                ),
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
            elif "status" in filters.ordering:
                ordering_field = filters.ordering.replace("status", "status_order")
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

    def get_agents_custom_status_and_rooms(self, filters: Filters, project):
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
            start_time = pendulum_parse(filters.start_date, tzinfo=tz)
            end_time = pendulum_parse(filters.end_date + " 23:59:59", tzinfo=tz)
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

        has_active_custom_status_subquery_2 = Exists(
            CustomStatus.objects.filter(
                user=OuterRef("email"),
                status_type__project=project,
                is_active=True,
            ).exclude(status_type__name__iexact="in-service")
        )

        agents_query = (
            agents_query.filter(project_permissions__project=project, is_active=True)
            .annotate(
                status=Subquery(project_permission_queryset),
                has_active_custom_status=has_active_custom_status_subquery_2,
                status_order=Case(
                    When(Q(status='OFFLINE') & Q(has_active_custom_status=False), then=Value(1)),
                    When(has_active_custom_status=True, then=Value(2)),
                    When(Q(status='ONLINE') & Q(has_active_custom_status=False), then=Value(3)),
                    default=Value(2),
                    output_field=IntegerField(),
                ),
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
            if "status" in filters.ordering:
                ordering_field = filters.ordering.replace("status", "status_order")
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
            "custom_status",
        )

        return agents_query

    def _get_agents_query(self, filters: Filters, project: Project):
        agents = self.model.filter(project_permissions__project=project)

        if not filters.is_weni_admin:
            agents = agents.exclude(get_admin_domains_exclude_filter())

        if filters.agent:
            agents = agents.filter(email=filters.agent)

        if filters.queue:
            agents = agents.filter(
                project_permissions__queue_authorizations__queue=filters.queue
            )
        elif filters.sector:
            agents = agents.filter(
                project_permissions__queue_authorizations__queue__sector__in=filters.sector
            )

        return agents

    def _get_custom_status_query(self, filters: Filters, project: Project):
        custom_status = CustomStatus.objects.filter(
            Q(
                user=OuterRef("email"),
            )
            & Q(
                status_type__project=project,
                status_type__is_deleted=False,
            )
            & ~Q(status_type__name__iexact="in-service")
        )

        tz = project.timezone
        tz_str = str(tz)

        if filters.start_date:
            start_time = parse_date_with_timezone(filters.start_date, tz_str)
        else:
            start_time = (
                timezone.now()
                .astimezone(tz)
                .replace(hour=0, minute=0, second=0, microsecond=0)
            )

        if filters.end_date:
            end_time = parse_date_with_timezone(
                filters.end_date, tz_str, is_end_date=True
            )
        else:
            end_time = timezone.now()

        custom_status = custom_status.filter(
            created_on__gte=start_time,
            created_on__lte=end_time,
        )

        return custom_status

    def get_agents_custom_status(
        self, filters: Filters, project: Project
    ) -> QuerySet[User]:
        agents = self._get_agents_query(filters, project)

        custom_status_base_query = self._get_custom_status_query(filters, project)

        custom_status_subquery = Subquery(
            custom_status_base_query.values("user")
            .annotate(
                aggregated=JSONBAgg(
                    JSONObject(
                        status_type=F("status_type__name"),
                        break_time=F("break_time"),
                    )
                )
            )
            .values("aggregated"),
            output_field=JSONField(),
        )

        agents = agents.annotate(
            custom_status=custom_status_subquery,
            agent=Concat(F("first_name"), Value(" "), F("last_name")),
        )

        ordering_fields = ["-agent", "agent"]

        if filters.ordering and filters.ordering in ordering_fields:
            agents = agents.order_by(filters.ordering)
        else:
            agents = agents.order_by("agent")

        return agents

    def _get_converted_dates(self, filters: Filters, project: Project) -> dict:
        project_timezone = project.timezone if project.timezone else "UTC"

        if not isinstance(project_timezone, str) and hasattr(project_timezone, "key"):
            project_timezone = project_timezone.key

        start_date = None
        end_date = None

        if filters.start_date:
            start_date = parse_date_with_timezone(
                filters.start_date, project_timezone, is_end_date=False
            )

        if filters.end_date:
            end_date = parse_date_with_timezone(
                filters.end_date, project_timezone, is_end_date=True
            )

        return start_date, end_date

    def _get_csat_general(self, filters: Filters, project: Project) -> CSATScoreGeneral:
        rooms_query = {
            "is_active": False,
            "queue__sector__project": project,
        }

        start_date, end_date = self._get_converted_dates(filters, project)

        filters_mapping = {
            "start_date": ("ended_at__gte", start_date),
            "end_date": ("ended_at__lte", end_date),
            "sector": ("queue__sector__in", filters.sector),
            "queue": ("queue", filters.queue),
            "tag": ("tags__in", filters.tags),
            "tags": ("tags__in", filters.tags),
            "queues": ("queue__in", filters.queues),
        }

        for filter_name, (query_expression, value) in filters_mapping.items():
            if value:
                rooms_query[query_expression] = value

        return CSATScoreGeneral(
            rooms=Room.objects.filter(**rooms_query).count(),
            reviews=Room.objects.filter(
                csat_survey__isnull=False,
                csat_survey__rating__isnull=False,
                **rooms_query,
            ).count(),
            avg_rating=Room.objects.filter(
                csat_survey__isnull=False,
                csat_survey__rating__isnull=False,
                **rooms_query,
            ).aggregate(avg_rating=Avg("csat_survey__rating"))["avg_rating"],
        )

    def _get_csat_agents(self, filters: Filters, project: Project) -> QuerySet[User]:
        agents = User.objects.filter(project_permissions__project=project)

        if not filters.is_weni_admin:
            agents = agents.exclude(get_admin_domains_exclude_filter())

        if filters.agent:
            agents = agents.filter(email=filters.agent)
        return agents

    def _get_csat_rooms_query(self, filters: Filters, project: Project) -> dict:
        rooms_query = {
            "rooms__is_active": False,
            "rooms__queue__sector__project": project,
        }

        start_date, end_date = self._get_converted_dates(filters, project)

        filters_mapping = {
            "start_date": ("rooms__ended_at__gte", start_date),
            "end_date": ("rooms__ended_at__lte", end_date),
            "sector": ("rooms__queue__sector__in", filters.sector),
            "queue": ("rooms__queue", filters.queue),
            "tag": ("rooms__tags__in", filters.tags),
            "tags": ("rooms__tags__in", filters.tags),
            "queues": ("rooms__queue__in", filters.queues),
        }

        for filter_name, (query_expression, value) in filters_mapping.items():
            if value:
                rooms_query[query_expression] = value

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
                "rooms__csat_survey__uuid",
                distinct=False,
                filter=Q(**csat_reviews_query),
            ),
            avg_rating=Coalesce(
                Avg(
                    "rooms__csat_survey__rating",
                    filter=Q(**csat_reviews_query),
                ),
                Value(0.0),
            ),
        )

        return self._get_csat_general(filters, project), agents


class CSATRepository:
    def get_csat_ratings(self, filters: Filters, project) -> CSATRatings:
        filter_mapping = {
            "start_date": ("room__ended_at__gte", filters.start_date),
            "end_date": ("room__ended_at__lte", filters.end_date),
            "queues": ("room__queue__in", filters.queues),
            "sectors": ("room__queue__sector__in", filters.sectors),
            "tags": ("room__tags__in", filters.tags),
            "agent": ("room__user", filters.agent),
        }

        csat_query = {"room__queue__sector__project": project}

        for key, (field_name, filter_value) in filter_mapping.items():
            if filter_value is not None and filter_value != "":
                if field_name.endswith("__in") and not isinstance(filter_value, list):
                    filter_value = [filter_value]

                csat_query[field_name] = filter_value

        csat_ratings = (
            CSATSurvey.objects.filter(**csat_query)
            .values("rating")
            .annotate(count=Count("uuid"))
            .order_by("rating")
        )

        total_count = csat_ratings.aggregate(total=Sum("count"))["total"]

        ratings_counts = [
            CSATRatingCount(
                rating=rating["rating"],
                count=rating["count"],
                percentage=(
                    round((rating["count"] / total_count) * 100, 2)
                    if total_count
                    else 0.0
                ),
            )
            for rating in csat_ratings
        ]

        return CSATRatings(ratings=ratings_counts)
