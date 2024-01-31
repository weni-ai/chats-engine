import json
from urllib import parse

import pendulum
from django.conf import settings
from django.db.models import Avg, F
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework import serializers

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
            rooms_filter["tags__uuid"] = context.get("tag")
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


class DashboardAgentsSerializer(serializers.Serializer):
    first_name = serializers.CharField(allow_null=True, required=False)
    email = serializers.EmailField(allow_null=True, required=False)
    agent_status = serializers.CharField(allow_null=True, required=False)
    closed_rooms = serializers.IntegerField(allow_null=True, required=False)
    opened_rooms = serializers.IntegerField(allow_null=True, required=False)


class DashboardRawDataSerializer(serializers.Serializer):
    closed_rooms = serializers.IntegerField(allow_null=True, required=False)
    transfer_count = serializers.IntegerField(allow_null=True, required=False)
    queue_rooms = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["closed_rooms", "transfer_count", "queue_rooms"]


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
            rooms_filter["room__tags__uuid"] = context.get("tag")
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


class DashboardRawDataSerializer1(serializers.ModelSerializer):
    closed_rooms = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["closed_rooms"]


class DashboardRawDataSerializer2(serializers.ModelSerializer):
    transfer_count = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["transfer_count"]


class DashboardRawDataSerializer3(serializers.ModelSerializer):
    queue_rooms = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["queue_rooms"]
