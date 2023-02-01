from django.conf import settings

from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from rest_framework import serializers

from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization

from chats.apps.rooms.models import Room
from django.db.models import Sum, Count, Q, Avg
from chats.apps.sectors.models import Sector, SectorTag


class DashboardRoomsSerializer(serializers.ModelSerializer):

    active_chats = serializers.SerializerMethodField()
    interact_time = serializers.SerializerMethodField()
    response_time = serializers.SerializerMethodField()
    waiting_time = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ["active_chats", "interact_time", "response_time", "waiting_time"]

    def get_active_chats(self, project):
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
            rooms_filter["is_active"] = True
            rooms_filter["created_on__gte"] = initial_datetime

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

        metrics_rooms_count = Room.objects.filter(**rooms_filter).count()
        interaction = Room.objects.filter(**rooms_filter).aggregate(
            waiting_time=Sum("metric__waiting_time")
        )

        if interaction and metrics_rooms_count > 0:
            response_time = interaction["waiting_time"] / metrics_rooms_count
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
                self.context.get("end_date"),
            ]
        else:
            rooms_filter["user__rooms__created_on__gte"] = initial_datetime
            rooms_filter["user__rooms__is_active"] = True
            permission_filter["status"] = "ONLINE"
        if self.context.get("sector"):
            rooms_filter["user__rooms__queue__sector"] = self.context.get("sector")
            if self.context.get("tag"):
                rooms_filter["user__rooms__tags__name"] = self.context.get("tag")
        else:
            rooms_filter["user__rooms__queue__sector__project"] = project

        queue_auth = (
            ProjectPermission.objects.filter(**permission_filter)
            .values("user__email")
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

        if self.context.get("sector"):
            model = Queue
            rooms_filter_prefix = ""
            model_filter = {"sector": self.context.get("sector")}
            rooms_filter["rooms__queue__sector"] = self.context.get("sector")
            if self.context.get("tag"):
                rooms_filter["rooms__tags__name"] = self.context.get("tag")
        else:
            rooms_filter[
                f"{rooms_filter_prefix}rooms__queue__sector__project"
            ] = project

        if self.context.get("start_date") and self.context.get("end_date"):
            rooms_filter[f"{rooms_filter_prefix}rooms__created_on__range"] = [
                self.context.get("start_date"),
                self.context.get("end_date"),
            ]
            # SE EU NAO ADD AQUI DENTRO, DA ERRO AO FILTRAR PASSANDO SETOR COM DATA
            online_agents = Count(f"{rooms_filter_prefix}rooms")

        else:
            rooms_filter[
                f"{rooms_filter_prefix}rooms__created_on__gte"
            ] = initial_datetime
            online_agents_filter = {
                f"{rooms_filter_prefix}authorizations__permission__status": "ONLINE"
            }
            online_agents = Count(
                f"{rooms_filter_prefix}authorizations__permission",
                filter=Q(**online_agents_filter),
                distinct=True,
            )
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
                online_agents=online_agents,
            )
        )
        return results
