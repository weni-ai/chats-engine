from urllib import parse

from django.conf import settings
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework import serializers

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class DashboardRoomsSerializer(serializers.ModelSerializer):
    DASHBOARD_ROOMS_CACHE_KEY = "dashboard:{filter}:{metric}"

    active_chats = serializers.SerializerMethodField()
    interact_time = serializers.SerializerMethodField()
    response_time = serializers.SerializerMethodField()
    waiting_time = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "active_chats",
            "interact_time",
            "response_time",
            "waiting_time",
        ]

    def __init__(self, *args, **kwargs):
        self.redis_connection = get_redis_connection()
        super().__init__(*args, **kwargs)

    def get_active_chats(self, project):
        rooms_filter = {}

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter["created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date")
                + " 23:59:59",  # TODO: USE DATETIME IN END DATE
            ]
            rooms_filter["is_active"] = False
            rooms_filter["user__isnull"] = False
        else:
            rooms_filter["user__isnull"] = False
            rooms_filter["is_active"] = True

        if self.context.get("agent"):
            rooms_filter["user"] = self.context.get("agent")

        if self.context.get("sector"):
            rooms_filter["queue__sector"] = self.context.get("sector")
            if self.context.get("tag"):
                rooms_filter["tags__name"] = self.context.get("tag")
        else:
            rooms_filter["queue__sector__project"] = project

        active_chats = Room.objects.filter(**rooms_filter).count()

        return active_chats

    def get_interact_time(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        rooms_filter = {}
        rooms_filter["user__isnull"] = False

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter["created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date")
                + " 23:59:59",  # TODO: USE DATETIME IN END DATE
            ]
        else:
            rooms_filter["created_on__gte"] = initial_datetime

        if self.context.get("agent"):
            rooms_filter["user"] = self.context.get("agent")

        if self.context.get("sector"):
            rooms_filter["queue__sector"] = self.context.get("sector")
            if self.context.get("tag"):
                rooms_filter["tags__name"] = self.context.get("tag")
        else:
            rooms_filter["queue__sector__project"] = project.uuid

        rooms_filter_interact_time_key = self.DASHBOARD_ROOMS_CACHE_KEY.format(
            filter=parse.urlencode(rooms_filter), metric="interact_time"
        )

        redis_interact_time_value = self.redis_connection.get(
            rooms_filter_interact_time_key
        )
        if redis_interact_time_value:
            return float(redis_interact_time_value)

        metrics_rooms_count = Room.objects.filter(**rooms_filter).count()
        interaction = Room.objects.filter(**rooms_filter).aggregate(
            interaction_time=Sum("metric__interaction_time")
        )

        if interaction and metrics_rooms_count > 0:
            interaction_time = interaction["interaction_time"] / metrics_rooms_count
        else:
            interaction_time = 0

        self.redis_connection.set(
            rooms_filter_interact_time_key, interaction_time, settings.CHATS_CACHE_TIME
        )

        return interaction_time

    def get_response_time(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        rooms_filter = {}
        rooms_filter["user__isnull"] = False

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter["created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date")
                + " 23:59:59",  # TODO: USE DATETIME IN END DATE
            ]
        else:
            rooms_filter["created_on__gte"] = initial_datetime

        if self.context.get("agent"):
            rooms_filter["user"] = self.context.get("agent")

        if self.context.get("sector"):
            rooms_filter["queue__sector"] = self.context.get("sector")
            if self.context.get("tag"):
                rooms_filter["tags__name"] = self.context.get("tag")
        else:
            rooms_filter["queue__sector__project__uuid"] = project.uuid

        rooms_filter_response_time_key = self.DASHBOARD_ROOMS_CACHE_KEY.format(
            filter=parse.urlencode(rooms_filter), metric="response_time"
        )

        redis_response_time_value = self.redis_connection.get(
            rooms_filter_response_time_key
        )

        if redis_response_time_value:
            return float(redis_response_time_value)

        metrics_rooms_count = Room.objects.filter(**rooms_filter).count()
        interaction = Room.objects.filter(**rooms_filter).aggregate(
            message_response_time=Sum("metric__message_response_time")
        )
        if interaction and metrics_rooms_count > 0:
            response_time = interaction["message_response_time"] / metrics_rooms_count
        else:
            response_time = 0

        self.redis_connection.set(
            rooms_filter_response_time_key, response_time, settings.CHATS_CACHE_TIME
        )

        return response_time

    def get_waiting_time(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        rooms_filter = {}
        rooms_filter["user__isnull"] = False

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter["created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date")
                + " 23:59:59",  # TODO: USE DATETIME IN END DATE
            ]
        else:
            rooms_filter["created_on__gte"] = initial_datetime

        if self.context.get("agent"):
            rooms_filter["user"] = self.context.get("agent")

        if self.context.get("sector"):
            rooms_filter["queue__sector"] = self.context.get("sector")
            if self.context.get("tag"):
                rooms_filter["tags__name"] = self.context.get("tag")
        else:
            rooms_filter["queue__sector__project__uuid"] = project.uuid

        rooms_filter_waiting_time_key = self.DASHBOARD_ROOMS_CACHE_KEY.format(
            filter=parse.urlencode(rooms_filter), metric="waiting_time"
        )

        redis_waiting_time_value = self.redis_connection.get(
            rooms_filter_waiting_time_key
        )

        if redis_waiting_time_value:
            return float(redis_waiting_time_value)

        metrics_rooms_count = Room.objects.filter(**rooms_filter).count()
        interaction = Room.objects.filter(**rooms_filter).aggregate(
            waiting_time=Sum("metric__waiting_time")
        )

        if interaction and metrics_rooms_count > 0:
            waiting_time = interaction["waiting_time"] / metrics_rooms_count
        else:
            waiting_time = 0

        self.redis_connection.set(
            rooms_filter_waiting_time_key, waiting_time, settings.CHATS_CACHE_TIME
        )

        return waiting_time


class DashboardAgentsSerializer(serializers.Serializer):
    project_agents = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "agents",
        ]

    def get_project_agents(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        rooms_filter = {}
        closed_rooms = {}
        permission_filter = {"project": project}

        closed_rooms["user__rooms__is_active"] = False
        rooms_filter["user__rooms__is_active"] = True

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter["user__rooms__created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date")
                + " 23:59:59",  # TODO: USE DATETIME IN END DATE
            ]
            closed_rooms["user__rooms__ended_at__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date")
                + " 23:59:59",  # TODO: USE DATETIME IN END DATE
            ]
        else:
            closed_rooms["user__rooms__ended_at__gte"] = initial_datetime

        if self.context.get("agent"):
            rooms_filter["user"] = self.context.get("agent")
            closed_rooms["user"] = self.context.get("agent")

        if self.context.get("sector"):
            rooms_filter["user__rooms__queue__sector"] = self.context.get("sector")
            closed_rooms["user__rooms__queue__sector"] = self.context.get("sector")
            if self.context.get("tag"):
                rooms_filter["user__rooms__tags__name"] = self.context.get("tag")
                closed_rooms["user__rooms__tags__name"] = self.context.get("tag")
        else:
            rooms_filter["user__rooms__queue__sector__project"] = project
            closed_rooms["user__rooms__queue__sector__project"] = project

        if "weni" in self.context.get("user_request"):
            queue_auth = (
                ProjectPermission.objects.filter(**permission_filter)
                .values("user__first_name")
                .annotate(
                    opened_rooms=Count(
                        "user__rooms",
                        filter=Q(**rooms_filter),
                        distinct=True,
                    ),
                    closed_rooms=Count(
                        "user__rooms",
                        filter=Q(**closed_rooms),
                        distinct=True,
                    ),
                )
            )
        else:
            queue_auth = (
                ProjectPermission.objects.filter(**permission_filter)
                .exclude(user__email__icontains="weni")
                .values("user__first_name")
                .annotate(
                    opened_rooms=Count(
                        "user__rooms",
                        filter=Q(**rooms_filter),
                        distinct=True,
                    ),
                    closed_rooms=Count(
                        "user__rooms",
                        filter=Q(**closed_rooms),
                        distinct=True,
                    ),
                )
            )

        return queue_auth


class DashboardSectorSerializer(serializers.ModelSerializer):
    sectors = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "sectors",
        ]

    def get_sectors(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        model = Sector
        rooms_filter = {}
        model_filter = {"project": project}
        rooms_filter_prefix = "queues__"

        if self.context.get("sector"):
            model = Queue
            rooms_filter_prefix = ""
            model_filter = {"sector": self.context.get("sector")}
            rooms_filter["rooms__queue__sector"] = self.context.get("sector")
            rooms_filter["rooms__user__isnull"] = False
            if self.context.get("tag"):
                rooms_filter["rooms__tags__name"] = self.context.get("tag")
            if self.context.get("agent"):
                rooms_filter["rooms__user"] = self.context.get("agent")
        else:
            rooms_filter[
                f"{rooms_filter_prefix}rooms__queue__sector__project"
            ] = project
            rooms_filter[f"{rooms_filter_prefix}rooms__user__isnull"] = False
            if self.context.get("agent"):
                rooms_filter[f"{rooms_filter_prefix}rooms__user"] = self.context.get(
                    "agent"
                )

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter[f"{rooms_filter_prefix}rooms__created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date")
                + " 23:59:59",  # TODO: USE DATETIME IN END DATE
            ]
        else:
            rooms_filter[
                f"{rooms_filter_prefix}rooms__created_on__gte"
            ] = initial_datetime

        results = (
            model.objects.filter(**model_filter)
            .values("name")
            .annotate(
                waiting_time=Avg(
                    f"{rooms_filter_prefix}rooms__metric__waiting_time",
                    filter=Q(**rooms_filter),
                ),
                response_time=Avg(
                    f"{rooms_filter_prefix}rooms__metric__message_response_time",
                    filter=Q(**rooms_filter),
                ),
                interact_time=Avg(
                    f"{rooms_filter_prefix}rooms__metric__interaction_time",
                    filter=Q(**rooms_filter),
                ),
            )
        )
        return results


class DashboardDataSerializer(serializers.ModelSerializer):
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
