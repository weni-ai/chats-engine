from django.contrib.postgres.aggregates import JSONBAgg
from django.contrib.postgres.fields import JSONField
from django.db.models import (
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

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.dto import get_admin_domains_exclude_filter
from chats.apps.projects.models import ProjectPermission
from chats.apps.projects.models.models import CustomStatus

from .dto import Filters


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
        
        if filters.agent:
            agents_filters &= Q(uuid=filters.agent)
        
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

        if agents_filter:
            agents_query = agents_query.filter(**agents_filter).distinct()

        agents_filters_custom = Q(project_permissions__project=project) & Q(is_active=True)
        if filters.agent:
            agents_filters_custom &= Q(uuid=filters.agent)

        agents_query = (
            agents_query.filter(agents_filters_custom)
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
