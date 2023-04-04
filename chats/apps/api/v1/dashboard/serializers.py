from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from rest_framework import serializers

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue

from chats.apps.rooms.models import Room
from django.db.models import (
    Sum,
    Count,
    Q,
    F,
    Avg,
    ExpressionWrapper,
    IntegerField,
    OuterRef,
    Subquery,
)
from chats.apps.sectors.models import Sector
from django.db.models import FloatField, Case, When
from django.db.models.functions import Cast
from django.db.models.functions.comparison import NullIf


class DashboardRoomsSerializer(serializers.ModelSerializer):

    active_chats = serializers.SerializerMethodField()
    interact_time = serializers.SerializerMethodField()
    response_time = serializers.SerializerMethodField()
    waiting_time = serializers.SerializerMethodField()
    transfer_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "active_chats",
            "interact_time",
            "response_time",
            "waiting_time",
            "transfer_percentage",
        ]

    def get_active_chats(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        rooms_filter = {}

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter["created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date")
                + " 23:59:59",  # TODO: USE DATETIME IN END DATE
            ]
            rooms_filter["is_active"] = False
        else:
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
            rooms_filter["queue__sector__project"] = project

        metrics_rooms_count = Room.objects.filter(**rooms_filter).count()
        interaction = Room.objects.filter(**rooms_filter).aggregate(
            interaction_time=Sum("metric__interaction_time")
        )

        if interaction and metrics_rooms_count > 0:
            interaction_time = interaction["interaction_time"] / metrics_rooms_count
        else:
            interaction_time = 0

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
            rooms_filter["queue__sector__project"] = project

        metrics_rooms_count = Room.objects.filter(**rooms_filter).count()
        interaction = Room.objects.filter(**rooms_filter).aggregate(
            message_response_time=Sum("metric__message_response_time")
        )
        if interaction and metrics_rooms_count > 0:
            response_time = interaction["message_response_time"] / metrics_rooms_count
        else:
            response_time = 0

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
            rooms_filter["queue__sector__project"] = project

        metrics_rooms_count = Room.objects.filter(**rooms_filter).count()
        interaction = Room.objects.filter(**rooms_filter).aggregate(
            waiting_time=Sum("metric__waiting_time")
        )

        if interaction and metrics_rooms_count > 0:
            response_time = interaction["waiting_time"] / metrics_rooms_count
        else:
            response_time = 0

        return response_time

    def get_transfer_percentage(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        rooms_filter = {}
        percentage_filter = {}

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

        percentage_filter = rooms_filter.copy()
        percentage_filter[f"metric__transfer_count__gt"] = 0

        metrics_rooms_count = Room.objects.filter(**rooms_filter).count()
        interaction = Room.objects.filter(**percentage_filter).aggregate(
            waiting_time=Count("metric__waiting_time")
        )

        response_time = 0
        if interaction and metrics_rooms_count > 0:
            response_time = interaction["waiting_time"] / metrics_rooms_count * 100
        else:
            response_time = 0

        return response_time


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
        permission_filter = {"project": project}

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter["user__rooms__created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date")
                + " 23:59:59",  # TODO: USE DATETIME IN END DATE
            ]
            rooms_filter["user__rooms__is_active"] = False
        else:
            rooms_filter["user__rooms__is_active"] = True
            permission_filter["status"] = "ONLINE"

        if self.context.get("agent"):
            rooms_filter["user"] = self.context.get("agent")

        if self.context.get("sector"):
            rooms_filter["user__rooms__queue__sector"] = self.context.get("sector")
            if self.context.get("tag"):
                rooms_filter["user__rooms__tags__name"] = self.context.get("tag")
        else:
            rooms_filter["user__rooms__queue__sector__project"] = project

        queue_auth = (
            ProjectPermission.objects.filter(**permission_filter)
            .values("user__first_name")
            .annotate(
                count=Count(
                    "user__rooms",
                    filter=Q(**rooms_filter),
                    distinct=True,
                )
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
        online_agents = Count(f"{rooms_filter_prefix}rooms")
        percentage_filter = {}

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
            online_agents_filter = {}
            online_agents_filter[f"{rooms_filter_prefix}rooms__created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date")
                + " 23:59:59",  # TODO: USE DATETIME IN END DATE
            ]
            online_agents_subquery = model.objects.annotate(
                online_agents=Count(f"{rooms_filter_prefix}rooms",
                filter=Q(**online_agents_filter)
                ),
            ).filter(pk=OuterRef("pk"))
        else:
            rooms_filter[
                f"{rooms_filter_prefix}rooms__created_on__gte"
            ] = initial_datetime
            online_agents_filter = {
                f"{rooms_filter_prefix}authorizations__permission__status": "ONLINE"
            }
            online_agents_subquery = model.objects.annotate(
                online_agents=Count(
                    "queues__authorizations__permission",
                    distinct=True,
                    filter=Q(**online_agents_filter),
                ),
            ).filter(pk=OuterRef("pk"))

        percentage_filter = rooms_filter.copy()
        percentage_filter[f"{rooms_filter_prefix}rooms__metric__transfer_count__gt"] = 0


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
                rooms_count=Count(
                    f"{rooms_filter_prefix}rooms__metric",
                    filter=Q(**rooms_filter),
                ),
                transfer_percentage=Case(
                    When(rooms_count=0, then=0),
                    default=ExpressionWrapper(
                        Count(
                            f"{rooms_filter_prefix}rooms__metric",
                            filter=Q(**percentage_filter),
                        )
                        / Cast(
                            F("rooms_count"),
                            output_field=FloatField(),
                        )
                        * 100,
                        output_field=FloatField(),
                    ),
                    output_field=FloatField(),
                ),
                online_agents=Subquery(
                    online_agents_subquery.values("online_agents"),
                    output_field=IntegerField(),
                ),
            )
        )
        return results


class DashboardDataSerializer(serializers.ModelSerializer):

    closed_rooms = serializers.SerializerMethodField()
    transfer_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ["closed_rooms", "transfer_count"]

    def get_closed_rooms(self, project):
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
            rooms_filter["is_active"] = False
            rooms_filter["created_on__gte"] = initial_datetime

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
