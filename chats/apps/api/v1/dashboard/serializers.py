import json
from urllib import parse

import pendulum
from django.conf import settings
from django.db.models import Avg
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework import serializers

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

    # chave do cache será criada no repository do orm django
    # no else do room data service, vai chamar o repository orm e se tiver valor cria a chave
    # e chama o set passando essa chave criada mais o resultado da consulta, igual feito na linha 94.
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
    active_rooms = serializers.IntegerField(allow_null=True, required=False)
    closed_rooms = serializers.IntegerField(allow_null=True, required=False)
    transfer_count = serializers.IntegerField(allow_null=True, required=False)
    queue_rooms = serializers.IntegerField(allow_null=True, required=False)


# Maybe separate each serializer in it's own serializer module/file


class DashboardSectorSerializer(serializers.Serializer):
    name = serializers.CharField(allow_null=True, required=False)
    waiting_time = serializers.IntegerField(allow_null=True, required=False)
    response_time = serializers.IntegerField(allow_null=True, required=False)
    interact_time = serializers.IntegerField(allow_null=True, required=False)


class DashboardClosedRoomSerializer(serializers.ModelSerializer):
    closed_rooms = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["closed_rooms"]


class DashboardTransferCountSerializer(serializers.ModelSerializer):
    transfer_count = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["transfer_count"]


class DashboardQueueRoomsSerializer(serializers.ModelSerializer):
    queue_rooms = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["queue_rooms"]


class DashboardActiveRoomsSerializer(serializers.ModelSerializer):
    active_rooms = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["active_rooms"]


class DashboardRoomSerializer(serializers.Serializer):
    waiting_time = serializers.IntegerField(allow_null=True, required=False)
    response_time = serializers.IntegerField(allow_null=True, required=False)
    interact_time = serializers.IntegerField(allow_null=True, required=False)
