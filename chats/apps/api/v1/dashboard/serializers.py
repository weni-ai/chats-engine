from django.conf import settings

from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from rest_framework import serializers

from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue, QueueAuthorization

from chats.apps.rooms.models import Room
from django.db.models import Sum, Count, Q, Subquery, IntegerField

from chats.apps.sectors.models import Sector, SectorTag


class DashboardRoomsSerializer(serializers.ModelSerializer):

    active_chats = serializers.SerializerMethodField()
    interact_time = serializers.SerializerMethodField()
    response_time = serializers.SerializerMethodField()
    waiting_time = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["active_chats", "interact_time", "response_time", "waiting_time"]

    def get_active_chats(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        active_chats = Room.objects.filter(
            queue__sector__project=project,
            is_active=True,
            created_on__gte=initial_datetime,
        ).count()

        return active_chats

    def get_interact_time(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector__project=project, created_on__gte=initial_datetime
        ).count()
        interaction = RoomMetrics.objects.filter(
            room__queue__sector__project=project, created_on__gte=initial_datetime
        ).aggregate(interaction_time=Sum("interaction_time"))["interaction_time"]

        if interaction and metrics_rooms_count > 0:
            interaction_time = interaction / metrics_rooms_count
        else:
            interaction_time = 0

        return interaction_time

    def get_response_time(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector__project=project, created_on__gte=initial_datetime
        ).count()
        room_metric = RoomMetrics.objects.filter(
            room__queue__sector__project=project, created_on__gte=initial_datetime
        ).aggregate(message_response_time=Sum("message_response_time"))[
            "message_response_time"
        ]

        if room_metric and metrics_rooms_count > 0:
            response_time = room_metric / metrics_rooms_count
        else:
            response_time = 0

        return response_time

    def get_waiting_time(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector__project=project, created_on__gte=initial_datetime
        ).count()
        room_metric = RoomMetrics.objects.filter(
            room__queue__sector__project=project, created_on__gte=initial_datetime
        ).aggregate(waiting_time=Sum("waiting_time"))["waiting_time"]

        if room_metric and metrics_rooms_count > 0:
            response_time = room_metric / metrics_rooms_count
        else:
            response_time = 0

        return response_time


class DashboardAgentsSerializer(serializers.ModelSerializer):

    project_agents = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "project_agents",
        ]

    def get_project_agents(self, project):
        initial_datetime = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        queue_auth = (
            QueueAuthorization.objects.filter(
                queue__sector__project=project,
                queue__sector__project__permissions__status="ONLINE",
            )
            .values("permission__user__first_name")
            .annotate(
                count=Count(
                    "queue__rooms",
                    filter=Q(queue__rooms__is_active=True),
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
        sector = (
            Sector.objects.filter(project=project, created_on__gte=initial_datetime)
            .values("name")
            .annotate(
                waiting_time=Sum("queues__rooms__metric__waiting_time")
                / Count("queues__rooms__metric"),
                response_time=Sum("queues__rooms__metric__message_response_time")
                / Count("queues__rooms__metric"),
                interact_time=Sum("queues__rooms__metric__interaction_time")
                / Count("queues__rooms__metric"),
                online_agents=(
                    Count(
                        "project__permissions__status",
                        filter=Q(project__permissions__status="ONLINE"),
                        distinct=True,
                    )
                ),
            )
        )
        return sector


class DashboardTagRoomFilterSerializer(serializers.ModelSerializer):

    total_rooms_tag = serializers.SerializerMethodField()
    interact_time_rooms_tag = serializers.SerializerMethodField()
    response_time_rooms_tag = serializers.SerializerMethodField()
    waiting_time_rooms_tag = serializers.SerializerMethodField()

    class Meta:
        model = SectorTag
        fields = [
            "total_rooms_tag",
            "interact_time_rooms_tag",
            "response_time_rooms_tag",
            "waiting_time_rooms_tag",
        ]

    def get_total_rooms_tag(self, sector_tag):
        tag_rooms = Room.objects.filter(queue__sector=sector_tag.sector).count()
        return tag_rooms

    def get_interact_time_rooms_tag(self, sector_tag):
        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector=sector_tag.sector,
            room__queue__sector__tags__name=sector_tag.name,
        ).count()
        interaction = RoomMetrics.objects.filter(
            room__queue__sector=sector_tag.sector
        ).aggregate(interaction_time=Sum("interaction_time"))["interaction_time"]

        if interaction:
            interaction_time = interaction / metrics_rooms_count
        else:
            interaction_time = 0

        return interaction_time

    def get_response_time_rooms_tag(self, sector_tag):
        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector=sector_tag.sector,
            room__queue__sector__tags__name=sector_tag.name,
        ).count()
        room_metric = RoomMetrics.objects.filter(
            room__queue__sector=sector_tag.sector
        ).aggregate(message_response_time=Sum("message_response_time"))[
            "message_response_time"
        ]

        if room_metric and metrics_rooms_count > 0:
            response_time = room_metric / metrics_rooms_count
        else:
            response_time = 0

        return response_time

    def get_waiting_time_rooms_tag(self, sector_tag):
        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector=sector_tag.sector,
            room__queue__sector__tags__name=sector_tag.name,
        ).count()

        room_metric = RoomMetrics.objects.filter(
            room__queue__sector=sector_tag.sector
        ).aggregate(waiting_time=Sum("waiting_time"))["waiting_time"]

        if room_metric and metrics_rooms_count > 0:
            response_time = room_metric / metrics_rooms_count
        else:
            response_time = 0

        return response_time


class DashboardTagAgentFilterSerializer(serializers.ModelSerializer):

    agent_tags = serializers.SerializerMethodField()

    class Meta:
        model = Sector
        fields = [
            "agent_tags",
        ]

    def get_agent_tags(self, sector):
        name = self.context.get("name")

        agents_rooms_tags = (
            sector.tags.filter(name=name)
            .values("rooms__user")
            .annotate(
                count=Count("rooms"),
                filter=Q(rooms__is_active=True, rooms__user__isnull=False),
            )
        )
        return agents_rooms_tags


class DashboardTagQueueFilterSerializer(serializers.ModelSerializer):

    queues = serializers.SerializerMethodField()

    class Meta:
        model = SectorTag
        fields = [
            "queues",
        ]

    def get_queues(self, sector_tag):
        queues = (
            Queue.objects.filter(
                sector=sector_tag.sector, sector__tags__name=sector_tag.name
            )
            .values("name")
            .annotate(
                waiting_time=Sum("rooms__metric__waiting_time"),
                response_time=Sum("rooms__metric__message_response_time"),
                interact_time=Sum("rooms__metric__interaction_time"),
                total_agents=(Count("rooms__user", distinct=True)),
            )
        )

        return queues


class DashboardSectorFilterSerializer(serializers.ModelSerializer):
    total_rooms_sector = serializers.SerializerMethodField()
    interact_time_rooms_sector = serializers.SerializerMethodField()
    response_time_rooms_sector = serializers.SerializerMethodField()
    waiting_time_rooms_sector = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "total_rooms_sector",
            "interact_time_rooms_sector",
            "response_time_rooms_sector",
            "waiting_time_rooms_sector",
        ]

    def get_total_rooms_sector(self, sector):
        sector_rooms = Room.objects.filter(queue__sector=sector).count()
        return sector_rooms

    def get_interact_time_rooms_sector(self, sector):
        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector=sector
        ).count()
        interaction = RoomMetrics.objects.filter(
            room__queue__sector=sector.sector
        ).aggregate(interaction_time=Sum("interaction_time"))["interaction_time"]

        if interaction:
            interaction_time = interaction / metrics_rooms_count
        else:
            interaction_time = 0

        return interaction_time

    def get_response_time_rooms_sector(self, sector):
        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector=sector
        ).count()
        room_metric = RoomMetrics.objects.filter(
            room__queue__sector=sector.sector
        ).aggregate(message_response_time=Sum("message_response_time"))[
            "message_response_time"
        ]

        if room_metric and metrics_rooms_count > 0:
            response_time = room_metric / metrics_rooms_count
        else:
            response_time = 0

        return response_time

    def get_waiting_time_rooms_sector(self, sector):
        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector=sector.sector
        ).count()
        room_metric = RoomMetrics.objects.filter(
            room__queue__sector=sector.sector
        ).aggregate(waiting_time=Sum("waiting_time"))["waiting_time"]

        if room_metric and metrics_rooms_count > 0:
            response_time = room_metric / metrics_rooms_count
        else:
            response_time = 0

        return response_time


class DashboardSectorAgentFilterSerializer(serializers.ModelSerializer):

    agent_sector = serializers.SerializerMethodField()

    class Meta:
        model = Sector
        fields = [
            "agent_sector",
        ]

    def get_agent_sector(self, sector):
        agents_sector = (
            QueueAuthorization.objects.filter(
                permission__status="OFFLINE", queue__sector=sector
            )
            .annotate(
                count_rooms=Count(
                    "permission__user__rooms",
                    filter=Q(permission__user__rooms__is_active=True),
                )
            )
            .values("permission__user__email", "count_rooms")
            .distinct()
        )

        return agents_sector


class DashboardSectorQueueFilterSerializer(serializers.ModelSerializer):

    queues = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "queues",
        ]

    def get_queues(self, sector):
        queues = (
            Queue.objects.filter(sector=sector)
            .values("name")
            .annotate(
                waiting_time=Sum("rooms__metric__waiting_time"),
                response_time=Sum("rooms__metric__message_response_time"),
                interact_time=Sum("rooms__metric__interaction_time"),
                total_agents=(Count("rooms__user", distinct=True)),
            )
        )

        return queues


class DashboardDateSectorFilterSerializer(serializers.ModelSerializer):
    total_rooms_sector = serializers.SerializerMethodField()
    interact_time_rooms_sector = serializers.SerializerMethodField()
    response_time_rooms_sector = serializers.SerializerMethodField()
    waiting_time_rooms_sector = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "total_rooms_sector",
            "interact_time_rooms_sector",
            "response_time_rooms_sector",
            "waiting_time_rooms_sector",
        ]

    def get_total_rooms_sector(self, sector):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        sector_rooms = Room.objects.filter(
            queue__sector=sector, created_on__range=[start_date, end_date]
        ).count()

        return sector_rooms

    def get_interact_time_rooms_sector(self, sector):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector=sector, room__created_on__range=[start_date, end_date]
        ).count()
        interaction = RoomMetrics.objects.filter(
            room__queue__sector=sector, room__created_on__range=[start_date, end_date]
        ).aggregate(interaction_time=Sum("interaction_time"))["interaction_time"]

        if interaction:
            interaction_time = interaction / metrics_rooms_count
        else:
            interaction_time = 0

        return interaction_time

    def get_response_time_rooms_sector(self, sector):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector=sector, room__created_on__range=[start_date, end_date]
        ).count()
        room_metric = RoomMetrics.objects.filter(
            room__queue__sector=sector, room__created_on__range=[start_date, end_date]
        ).aggregate(message_response_time=Sum("message_response_time"))[
            "message_response_time"
        ]

        if room_metric and metrics_rooms_count > 0:
            response_time = room_metric / metrics_rooms_count
        else:
            response_time = 0

        return response_time

    def get_waiting_time_rooms_sector(self, sector):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector=sector, room__created_on__range=[start_date, end_date]
        ).count()
        room_metric = RoomMetrics.objects.filter(
            room__queue__sector=sector, room__created_on__range=[start_date, end_date]
        ).aggregate(waiting_time=Sum("waiting_time"))["waiting_time"]

        if room_metric and metrics_rooms_count > 0:
            response_time = room_metric / metrics_rooms_count
        else:
            response_time = 0

        return response_time


class DashboardDateProjectFilterSerializer(serializers.ModelSerializer):

    active_chats = serializers.SerializerMethodField()
    interact_time = serializers.SerializerMethodField()
    response_time = serializers.SerializerMethodField()
    waiting_time = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["active_chats", "interact_time", "response_time", "waiting_time"]

    def get_active_chats(self, project):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        project_rooms = Room.objects.filter(
            queue__sector__project=project,
            is_active=True,
            created_on__range=[start_date, end_date],
        ).count()

        return project_rooms

    def get_interact_time(self, project):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector__project=project,
            room__created_on__range=[start_date, end_date],
        ).count()
        interaction = RoomMetrics.objects.filter(
            room__queue__sector__project=project,
            room__created_on__range=[start_date, end_date],
        ).aggregate(interaction_time=Sum("interaction_time"))["interaction_time"]

        if interaction:
            interaction_time = interaction / metrics_rooms_count
        else:
            interaction_time = 0

        return interaction_time

    def get_response_time(self, project):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector__project=project,
            room__created_on__range=[start_date, end_date],
        ).count()
        room_metric = RoomMetrics.objects.filter(
            room__queue__sector__project=project
        ).aggregate(message_response_time=Sum("message_response_time"))[
            "message_response_time"
        ]

        if room_metric and metrics_rooms_count > 0:
            response_time = room_metric / metrics_rooms_count
        else:
            response_time = 0

        return response_time

    def get_waiting_time(self, project):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        metrics_rooms_count = RoomMetrics.objects.filter(
            room__queue__sector__project=project,
            room__created_on__range=[start_date, end_date],
        ).count()
        room_metric = RoomMetrics.objects.filter(
            room__queue__sector__project=project,
            room__created_on__range=[start_date, end_date],
        ).aggregate(waiting_time=Sum("waiting_time"))["waiting_time"]

        if room_metric and metrics_rooms_count > 0:
            response_time = room_metric / metrics_rooms_count
        else:
            response_time = 0

        return response_time


class DashboardDateAgentsSectorFilterSerializer(serializers.ModelSerializer):

    sector_agents = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "sector_agents",
        ]

    def get_sector_agents(self, sector):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        queue_auth = (
            QueueAuthorization.objects.filter(
                queue__sector=sector,
                queue__sector__project__permissions__status="ONLINE",
                created_on__range=[start_date, end_date],
            )
            .values("permission__user__first_name")
            .annotate(
                count=Count(
                    "queue__rooms",
                    filter=Q(queue__rooms__is_active=True),
                    distinct=True,
                )
            )
        )
        return queue_auth


class DashboardDateAgentsProjectFilterSerializer(serializers.ModelSerializer):

    project_agents = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "project_agents",
        ]

    def get_project_agents(self, project):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        queue_auth = (
            QueueAuthorization.objects.filter(
                queue__sector__project=project,
                queue__sector__project__permissions__status="ONLINE",
                created_on__range=[start_date, end_date],
            )
            .annotate(
                count_rooms=Count(
                    "permission__user__rooms",
                    filter=Q(permission__user__rooms__is_active=True),
                )
            )
            .values("permission__user__email", "count_rooms")
            .distinct()
        )
        return queue_auth


class DashboardDateQueueSerializer(serializers.ModelSerializer):

    queues = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "queues",
        ]

    def get_queues(self, sector):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        queues = (
            Queue.objects.filter(
                sector=sector, created_on__range=[start_date, end_date]
            )
            .values("name")
            .annotate(
                waiting_time=Sum("rooms__metric__waiting_time"),
                response_time=Sum("rooms__metric__message_response_time"),
                interact_time=Sum("rooms__metric__interaction_time"),
            )
        )
        return queues


class DashboardDateSectorSerializer(serializers.ModelSerializer):

    sectors = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "sectors",
        ]

    def get_sectors(self, sector):
        start_date = self.context.get("start_date")
        end_date = self.context.get("end_date")

        sectors = (
            Sector.objects.filter(uuid=sector, created_on__range=[start_date, end_date])
            .values("name")
            .annotate(
                waiting_time=Sum("queues__rooms__metric__waiting_time"),
                response_time=Sum("queues__rooms__metric__message_response_time"),
                interact_time=Sum("queues__rooms__metric__interaction_time"),
                # online_agents=(Count("project__permissions__status", distinct=True)),
            )
        )
        return sectors
