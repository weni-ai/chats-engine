import json
from urllib import parse

import pendulum
from django.conf import settings
from django.db.models import Avg, Count, F, OuterRef, Q, Subquery, Sum
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework import serializers

from chats.apps.accounts.models import User
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models import ProjectPermission
from chats.apps.rooms.models import Room


def dashboard_general_data(context: dict, project):
    DASHBOARD_ROOMS_CACHE_KEY = "dashboard:{filter}:{metric}"
    redis_connection = get_redis_connection()

    tz = project.timezone
    initial_datetime = (
        timezone.now().astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    rooms_filter = {}
    active_chat_filter = {}
    rooms_filter["user__isnull"] = False

    user_request = ProjectPermission.objects.get(
        user=context.get("user_request"), project=project
    )
    rooms_query = Room.objects

    if context.get("start_date") and context.get("end_date"):
        start_time = pendulum.parse(context.get("start_date")).replace(tzinfo=tz)
        end_time = pendulum.parse(context.get("end_date") + " 23:59:59").replace(
            tzinfo=tz
        )

        rooms_filter["created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
        active_chat_filter["is_active"] = False
        active_chat_filter["user__isnull"] = False
    else:
        rooms_filter["created_on__gte"] = initial_datetime
        # live active_chat_filter does not use the created on filter, as rooms can be delayed from older
        active_chat_filter["user__isnull"] = False
        active_chat_filter["is_active"] = True

    if context.get("agent"):
        rooms_filter["user"] = context.get("agent")

    if context.get("sector"):
        rooms_filter["queue__sector"] = context.get("sector")
        # rooms_query = Room.objects
        if context.get("tag"):
            rooms_filter["tags__name"] = context.get("tag")
    else:
        rooms_filter["queue__sector__project"] = project

    if user_request:
        rooms_query = rooms_query.filter(
            queue__sector__in=user_request.manager_sectors()
        )

    interact_time_agg = Avg("metric__interaction_time")
    message_response_time_agg = Avg("metric__message_response_time")
    waiting_time_agg = Avg("metric__waiting_time")

    rooms_filter_general_time_key = DASHBOARD_ROOMS_CACHE_KEY.format(
        filter=parse.urlencode(rooms_filter), metric="general_time"
    )
    redis_general_time_value = redis_connection.get(rooms_filter_general_time_key)

    if redis_general_time_value:
        if rooms_filter.get("created_on__gte"):
            rooms_filter.pop("created_on__gte")
        rooms_filter.update(active_chat_filter)
        active_chats_count = rooms_query.filter(**rooms_filter).count()
        # Maybe separate the active_chats_agg count into a subquery
        general_data = json.loads(redis_general_time_value)
        general_data["active_chats"] = active_chats_count
        return general_data

    general_data = rooms_query.filter(**rooms_filter).aggregate(
        interact_time=interact_time_agg,
        response_time=message_response_time_agg,
        waiting_time=waiting_time_agg,
    )

    redis_connection.set(
        rooms_filter_general_time_key,
        json.dumps(general_data),
        settings.CHATS_CACHE_TIME,
    )
    if rooms_filter.get("created_on__gte"):
        rooms_filter.pop("created_on__gte")
    rooms_filter.update(active_chat_filter)
    active_chats_count = rooms_query.filter(**rooms_filter).count()
    # Maybe separate the active_chats_agg count into a subquery
    general_data["active_chats"] = active_chats_count
    return general_data


# Maybe separate each serializer in it's own serializer module/file


def dashboard_agents_data(context, project):
    tz = project.timezone
    initial_datetime = (
        timezone.now().astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    )

    rooms_filter = {}
    closed_rooms = {"rooms__queue__sector__project": project}
    opened_rooms = {"rooms__queue__sector__project": project}
    if context.get("start_date") and context.get("end_date"):
        start_time = pendulum.parse(context.get("start_date")).replace(tzinfo=tz)
        end_time = pendulum.parse(context.get("end_date") + " 23:59:59").replace(
            tzinfo=tz
        )

        rooms_filter["rooms__created_on__range"] = [start_time, end_time]
        rooms_filter["rooms__is_active"] = False
        closed_rooms["rooms__ended_at__range"] = [start_time, end_time]

    else:
        closed_rooms["rooms__ended_at__gte"] = initial_datetime
        opened_rooms["rooms__is_active"] = True
        closed_rooms["rooms__is_active"] = False

    if context.get("agent"):
        rooms_filter["rooms__user"] = context.get("agent")

    if context.get("sector"):
        rooms_filter["rooms__queue__sector"] = context.get("sector")
        if context.get("tag"):
            rooms_filter["rooms__tags__name"] = context.get("tag")

    project_permission_subquery = ProjectPermission.objects.filter(
        project_id=project,
        user_id=OuterRef("email"),
    ).values("status")[:1]

    agents_query = User.objects
    if not context.get("is_weni_admin"):
        agents_query = agents_query.exclude(email__endswith="weni.ai")

    agents_query = (
        agents_query.filter(project_permissions__project=project)
        .annotate(
            agent_status=Subquery(project_permission_subquery),
            closed_rooms=Count("rooms", filter=Q(**closed_rooms, **rooms_filter)),
            opened_rooms=Count("rooms", filter=Q(**opened_rooms, **rooms_filter)),
        )
        .values("first_name", "email", "agent_status", "closed_rooms", "opened_rooms")
    )

    return agents_query


# Maybe separate each serializer in it's own serializer module/file


def dashboard_division_data(context, project=None):
    tz = project.timezone
    initial_datetime = (
        timezone.now().astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    rooms_filter = {}
    division_level = "room__queue__sector"

    user_request = ProjectPermission.objects.get(
        user=context.get("user_request"), project=project
    )
    room_metric_query = RoomMetrics.objects

    if context.get("sector"):
        division_level = "room__queue"
        rooms_filter["room__queue__sector"] = context.get("sector")
        if context.get("tag"):
            rooms_filter["room__tags__name"] = context.get("tag")
    else:
        rooms_filter["room__queue__sector__project"] = project
    rooms_filter["room__user__isnull"] = False

    if context.get("agent"):
        rooms_filter["room__user"] = context.get("agent")

    if context.get("start_date") and context.get("end_date"):
        start_time = pendulum.parse(context.get("start_date")).replace(tzinfo=tz)
        end_time = pendulum.parse(context.get("end_date") + " 23:59:59").replace(
            tzinfo=tz
        )
        rooms_filter["created_on__range"] = [start_time, end_time]
    else:
        rooms_filter["created_on__gte"] = initial_datetime

    if user_request:
        room_metric_query = room_metric_query.filter(
            room__queue__sector__in=user_request.manager_sectors()
        )

    return (
        room_metric_query.filter(**rooms_filter)  # date, project or sector
        .values(f"{division_level}__uuid")
        .annotate(
            name=F(f"{division_level}__name"),
            waiting_time=Avg("waiting_time"),
            response_time=Avg("message_response_time"),
            interact_time=Avg("interaction_time"),
        )
        .values("name", "waiting_time", "response_time", "interact_time")
    )


class DashboardRawDataSerializer(serializers.ModelSerializer):
    closed_rooms = serializers.SerializerMethodField()
    transfer_count = serializers.SerializerMethodField()
    queue_rooms = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ["closed_rooms", "transfer_count", "queue_rooms"]

    def get_closed_rooms(self, project):
        tz = project.timezone
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )

        user_request = ProjectPermission.objects.get(
            user=self.context.get("user_request"), project=project
        )
        rooms_query = Room.objects

        rooms_filter = {}
        rooms_filter["is_active"] = False

        if self.context.get("start_date") and self.context.get("end_date"):
            start_time = pendulum.parse(self.context.get("start_date")).replace(
                tzinfo=tz
            )
            end_time = pendulum.parse(
                self.context.get("end_date") + " 23:59:59"
            ).replace(tzinfo=tz)
            rooms_filter["ended_at__range"] = [start_time, end_time]
        else:
            rooms_filter["ended_at__gte"] = initial_datetime

        if self.context.get("sector"):
            rooms_filter["queue__sector"] = self.context.get("sector")
            if self.context.get("tag"):
                rooms_filter["tags__name"] = self.context.get("tag")
            if self.context.get("queue"):
                rooms_filter["queue"] = self.context.get("queue")
        else:
            rooms_filter["queue__sector__project"] = project

        if self.context.get("agent"):
            rooms_filter["user"] = self.context.get("agent")

        if user_request:
            rooms_query = rooms_query.filter(
                queue__sector__in=user_request.manager_sectors()
            )

        closed_rooms = rooms_query.filter(**rooms_filter).count()

        return closed_rooms

    def get_transfer_count(self, project):
        tz = project.timezone

        tz = project.timezone
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        rooms_filter = {}

        user_request = ProjectPermission.objects.get(
            user=self.context.get("user_request"), project=project
        )
        rooms_query = Room.objects

        if self.context.get("start_date") and self.context.get("end_date"):
            start_time = pendulum.parse(self.context.get("start_date")).replace(
                tzinfo=tz
            )
            end_time = pendulum.parse(
                self.context.get("end_date") + " 23:59:59"
            ).replace(tzinfo=tz)
            rooms_filter["created_on__range"] = [
                start_time,
                end_time,
            ]
        else:
            rooms_filter["created_on__gte"] = initial_datetime

        if self.context.get("sector"):
            rooms_filter["queue__sector"] = self.context.get("sector")
            if self.context.get("tag"):
                rooms_filter["tags__name"] = self.context.get("tag")
        else:
            rooms_filter["queue__sector__project"] = project

        if user_request:
            rooms_query = rooms_query.filter(
                queue__sector__in=user_request.manager_sectors()
            )

        transfer_metric = rooms_query.filter(**rooms_filter).aggregate(
            count=Sum("metric__transfer_count")
        )

        return transfer_metric["count"]

    def get_queue_rooms(self, project):
        tz = project.timezone
        rooms_filter = {}
        rooms_filter["user__isnull"] = True
        rooms_filter["is_active"] = True

        user_request = ProjectPermission.objects.get(
            user=self.context.get("user_request"), project=project
        )
        rooms_query = Room.objects

        if self.context.get("start_date") and self.context.get("end_date"):
            start_time = pendulum.parse(self.context.get("start_date")).replace(
                tzinfo=tz
            )
            end_time = pendulum.parse(
                self.context.get("end_date") + " 23:59:59"
            ).replace(tzinfo=tz)
            rooms_filter["created_on__range"] = [
                start_time,
                end_time,
            ]

        if self.context.get("sector"):
            rooms_filter["queue__sector"] = self.context.get("sector")
        else:
            rooms_filter["queue__sector__project"] = project

        if user_request:
            rooms_query = rooms_query.filter(
                queue__sector__in=user_request.manager_sectors()
            )

        queue_rooms_metric = rooms_query.filter(**rooms_filter).count()

        return queue_rooms_metric
