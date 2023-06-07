import json
from urllib import parse

from django.conf import settings
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework import serializers

from chats.apps.dashboard.models import RoomMetrics
from chats.apps.rooms.models import Room


def dashboard_general_data(context: dict, project):
    DASHBOARD_ROOMS_CACHE_KEY = "dashboard:{filter}:{metric}"
    redis_connection = get_redis_connection()

    initial_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    rooms_filter = {}
    active_chat_filter = {}
    rooms_filter["user__isnull"] = False
    if context.get("start_date") and context.get("end_date"):
        rooms_filter["created_on__range"] = [
            context.get("start_date"),
            context.get("end_date") + " 23:59:59",  # TODO: USE DATETIME IN END DATE
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
        if context.get("tag"):
            rooms_filter["tags__name"] = context.get("tag")
    else:
        rooms_filter["queue__sector__project"] = project

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
        active_chats_count = Room.objects.filter(**rooms_filter).count()
        # Maybe separate the active_chats_agg count into a subquery
        general_data = json.loads(redis_general_time_value)
        general_data["active_chats"] = active_chats_count
        return general_data

    general_data = Room.objects.filter(**rooms_filter).aggregate(
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
    active_chats_count = Room.objects.filter(**rooms_filter).count()
    # Maybe separate the active_chats_agg count into a subquery
    general_data["active_chats"] = active_chats_count
    return general_data


# Maybe separate each serializer in it's own serializer module/file


def dashboard_agents_data(context, project):
    initial_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    rooms_filter = {"user__isnull": False}
    closed_rooms = {}

    if context.get("start_date") and context.get("end_date"):
        rooms_filter["created_on__range"] = [
            context.get("start_date"),
            context.get("end_date") + " 23:59:59",  # TODO: USE DATETIME IN END DATE
        ]
    else:
        closed_rooms["ended_at__gte"] = initial_datetime

    if context.get("agent"):
        rooms_filter["user"] = context.get("agent")

    if context.get("sector"):
        rooms_filter["queue__sector"] = context.get("sector")
        if context.get("tag"):
            rooms_filter["tags__name"] = context.get("tag")
    else:
        rooms_filter["queue__sector__project"] = project

    agents_query = Room.objects
    if not context.get("is_weni_admin"):
        agents_query = agents_query.exclude(user__email__endswith="weni.ai")

    agents_query = (
        Room.objects.filter(**rooms_filter)
        .values("user")
        .annotate(
            user__first_name=F("user__first_name"),
            closed_rooms=Count("uuid", filter=Q(is_active=False, **closed_rooms)),
            opened_rooms=Count("uuid", filter=Q(is_active=True)),
        )
    )

    return agents_query


# Maybe separate each serializer in it's own serializer module/file


def dashboard_division_data(context, project=None):
    initial_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    rooms_filter = {}
    division_level = "room__queue__sector"

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
        rooms_filter["created_on__range"] = [
            context.get("start_date"),
            context.get("end_date") + " 23:59:59",  # TODO: USE DATETIME IN END DATE
        ]
    else:
        rooms_filter["created_on__gte"] = initial_datetime

    return (
        RoomMetrics.objects.filter(**rooms_filter)  # date, project or sector
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
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        rooms_filter = {}
        rooms_filter["is_active"] = False

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter["ended_at__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date"),
            ]
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

        closed_rooms = Room.objects.filter(**rooms_filter).count()

        return closed_rooms

    def get_transfer_count(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        rooms_filter = {}

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter["created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date"),
            ]
        else:
            rooms_filter["created_on__gte"] = initial_datetime

        if self.context.get("sector"):
            rooms_filter["queue__sector"] = self.context.get("sector")
            if self.context.get("tag"):
                rooms_filter["tags__name"] = self.context.get("tag")
        else:
            rooms_filter["queue__sector__project"] = project

        transfer_metric = Room.objects.filter(**rooms_filter).aggregate(
            count=Sum("metric__transfer_count")
        )

        return transfer_metric["count"]

    def get_queue_rooms(self, project):
        rooms_filter = {}
        rooms_filter["user__isnull"] = True
        rooms_filter["is_active"] = True

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter["created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date"),
            ]

        if self.context.get("sector"):
            rooms_filter["queue__sector"] = self.context.get("sector")
        else:
            rooms_filter["queue__sector__project"] = project

        queue_rooms_metric = Room.objects.filter(**rooms_filter).count()

        return queue_rooms_metric
