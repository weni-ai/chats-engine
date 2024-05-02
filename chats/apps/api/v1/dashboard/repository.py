import json
from typing import List
from urllib import parse

from django.conf import settings
from django.db.models import Avg, Count, F, OuterRef, Q, Subquery, Sum, FloatField
from django.utils import timezone
from django_redis import get_redis_connection
from pendulum.parser import parse as pendulum_parse

from chats.apps.accounts.models import User
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models import ProjectPermission
from chats.apps.rooms.models import Room

from .dto import (
    ActiveRoomData,
    Agent,
    ClosedRoomData,
    Filters,
    QueueRoomData,
    Sector,
    TransferRoomData,
)
from .interfaces import CacheRepository, RoomsDataRepository
from django.db.models.functions import Coalesce


class AgentRepository:
    def __init__(self):
        self.model = User.objects

    def get_agents_data(self, filters: Filters, project) -> List[Agent]:
        tz = project.timezone
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        rooms_filter = {}
        closed_rooms = {"rooms__queue__sector__project": project}
        opened_rooms = {"rooms__queue__sector__project": project}
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

        if filters.sector:
            rooms_filter["rooms__queue__sector"] = filters.sector
            if filters.tag:
                rooms_filter["rooms__tags__uuid"] = filters.tag

        project_permission_subquery = ProjectPermission.objects.filter(
            project_id=project,
            user_id=OuterRef("email"),
        ).values("status")[:1]

        agents_query = self.model
        if not filters.is_weni_admin:
            agents_query = agents_query.exclude(email__endswith="weni.ai")

        agents_query = (
            agents_query.filter(project_permissions__project=project, is_active=True)
            .annotate(
                agent_status=Subquery(project_permission_subquery),
                closed_rooms=Count("rooms", filter=Q(**closed_rooms, **rooms_filter)),
                opened_rooms=Count("rooms", filter=Q(**opened_rooms, **rooms_filter)),
            )
            .values(
                "first_name", "email", "agent_status", "closed_rooms", "opened_rooms"
            )
        )

        user_agents = [
            Agent(
                first_name=user_agent["first_name"],
                email=user_agent["email"],
                agent_status=user_agent["agent_status"],
                closed_rooms=user_agent["closed_rooms"],
                opened_rooms=user_agent["opened_rooms"],
            )
            for user_agent in agents_query
        ]

        return user_agents


class ClosedRoomsRepository:
    def __init__(self) -> None:
        self.model = Room.objects
        self.rooms_filter = {}

    def _filter_date_range(self, filters, tz):
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        self.rooms_filter["is_active"] = False

        if filters.start_date and filters.end_date:
            start_time = pendulum_parse(filters.start_date, tzinfo=tz)
            end_time = pendulum_parse(filters.end_date + " 23:59:59", tzinfo=tz)
            self.rooms_filter["ended_at__range"] = [start_time, end_time]

            return self.rooms_filter

        self.rooms_filter["ended_at__gte"] = initial_datetime
        return self.rooms_filter

    def _filter_sector(self, filters):
        if filters.sector:
            self.rooms_filter["queue__sector"] = filters.sector
            if filters.tag:
                self.rooms_filter["tags__uuid"] = filters.tag
            if filters.queue:
                self.rooms_filter["queue"] = filters.queue
            return self.rooms_filter

        self.rooms_filter["queue__sector__project"] = filters.project
        return self.rooms_filter

    def _filter_agents(self, filters):
        if filters.agent:
            self.rooms_filter["user"] = filters.agent
            return self.rooms_filter

    def closed_rooms(self, filters):
        tz = filters.project.timezone

        self._filter_date_range(filters, tz)
        self._filter_sector(filters)
        self._filter_agents(filters)

        user_agents = []
        if filters.user_request:
            rooms_query = self.model.filter(
                queue__sector__in=filters.user_request.manager_sectors()
            )
            closed_rooms = rooms_query.filter(**self.rooms_filter).count()
            user_agents = [ClosedRoomData(closed_rooms=closed_rooms)]
            return user_agents

        return user_agents


class TransferCountRepository:
    def __init__(self) -> None:
        self.model = Room.objects
        self.rooms_filter = {}

    def _filter_date_range(self, filters, tz):
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )

        if filters.start_date and filters.end_date:
            start_time = pendulum_parse(filters.start_date, tzinfo=tz)
            end_time = pendulum_parse(filters.end_date + " 23:59:59", tzinfo=tz)
            self.rooms_filter["created_on__range"] = [start_time, end_time]
            return self.rooms_filter

        self.rooms_filter["created_on__gte"] = initial_datetime
        return self.rooms_filter

    def _filter_sector(self, filters):
        if filters.sector:
            self.rooms_filter["queue__sector"] = filters.sector
            if filters.tag:
                self.rooms_filter["tags__uuid"] = filters.tag
            if filters.queue:
                self.rooms_filter["queue"] = filters.queue
            return self.rooms_filter

        self.rooms_filter["queue__sector__project"] = filters.project
        return self.rooms_filter

    def transfer_count(self, filters):
        tz = filters.project.timezone

        self._filter_date_range(filters, tz)
        self._filter_sector(filters)

        transfer_count = []
        if filters.user_request:
            rooms_query = self.model.filter(
                queue__sector__in=filters.user_request.manager_sectors()
            )

            transfer_metric = rooms_query.filter(**self.rooms_filter).aggregate(
                transfer_count=Sum("metric__transfer_count")
            )["transfer_count"]
            if transfer_metric is None:
                transfer_metric = 0

            transfer_count = [TransferRoomData(transfer_count=transfer_metric)]
            return transfer_count

        return transfer_count


class QueueRoomsRepository:
    def __init__(self) -> None:
        self.model = Room.objects
        self.rooms_filter = {}

    def _filter_date_range(self, filters, tz):
        self.rooms_filter["user__isnull"] = True
        self.rooms_filter["is_active"] = True

        if filters.start_date and filters.end_date:
            start_time = pendulum_parse(filters.start_date, tzinfo=tz)
            end_time = pendulum_parse(filters.end_date + " 23:59:59", tzinfo=tz)
            self.rooms_filter["created_on__range"] = [start_time, end_time]
            return self.rooms_filter

    def _filter_sector(self, filters):
        if filters.sector:
            self.rooms_filter["queue__sector"] = filters.sector
            return self.rooms_filter

        self.rooms_filter["queue__sector__project"] = filters.project
        return self.rooms_filter

    def queue_rooms(self, filters):
        tz = filters.project.timezone

        self._filter_date_range(filters, tz)
        self._filter_sector(filters)
        print(filters)
        queue_rooms = []
        if filters.user_request:
            rooms_query = self.model.filter(
                queue__sector__in=filters.user_request.manager_sectors()
            )

            queue_rooms_metric = rooms_query.filter(**self.rooms_filter).count()
            queue_rooms = [QueueRoomData(queue_rooms=queue_rooms_metric)]
            return queue_rooms

        return queue_rooms


class ActiveChatsRepository:
    def __init__(self) -> None:
        self.model = Room.objects
        self.rooms_filter = {}

    def _filter_date_range(self, filters, tz):
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        if filters.start_date and filters.end_date:
            start_time = pendulum_parse(filters.start_date, tzinfo=tz)
            end_time = pendulum_parse(filters.end_date + " 23:59:59", tzinfo=tz)
            self.rooms_filter["created_on__range"] = [start_time, end_time]
            self.rooms_filter["is_active"] = False
            self.rooms_filter["user__isnull"] = False
        else:
            self.rooms_filter["created_on__gte"] = initial_datetime
            self.rooms_filter["user__isnull"] = False
            self.rooms_filter["is_active"] = True

    def _filter_agents(self, filters):
        if filters.agent:
            self.rooms_filter["user"] = filters.agent

    def _filter_sector(self, filters):
        if filters.sector:
            self.rooms_filter["queue__sector"] = filters.sector
            # rooms_query = Room.objects
            if filters.tag:
                self.rooms_filter["tags__uuid"] = filters.tag
        else:
            self.rooms_filter["queue__sector__project"] = filters.project

    def active_chats(self, filters):
        tz = filters.project.timezone
        self._filter_date_range(filters, tz)
        self._filter_agents(filters)
        self._filter_sector(filters)

        if self.rooms_filter.get("created_on__gte"):
            self.rooms_filter.pop("created_on__gte")

        active_chats = []

        if filters.user_request:
            rooms_query = self.model.filter(
                queue__sector__in=filters.user_request.manager_sectors()
            )
            active_chats_count = rooms_query.filter(**self.rooms_filter).count()
            active_chats = [ActiveRoomData(active_rooms=active_chats_count)]
            return active_chats

        return active_chats


class SectorRepository:
    def __init__(self) -> None:
        self.model = RoomMetrics.objects.exclude(room__queue__is_deleted=True)
        self.rooms_filter = {}
        self.division_level = "room__queue__sector"
        self.rooms_filter["room__user__isnull"] = False

    def _filter_date_range(self, filters, tz):
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )

        if filters.start_date and filters.end_date:
            start_time = pendulum_parse(filters.start_date, tzinfo=tz)
            end_time = pendulum_parse(filters.end_date + " 23:59:59", tzinfo=tz)
            self.rooms_filter["created_on__range"] = [start_time, end_time]
            return self.rooms_filter
        else:
            self.rooms_filter["created_on__gte"] = initial_datetime
        return self.rooms_filter

    def _filter_sector(self, filters):
        if filters.sector:
            self.division_level = "room__queue"
            self.rooms_filter["room__queue__sector"] = filters.sector
            if filters.tag:
                self.rooms_filter["room__tags__uuid"] = filters.tag
        else:
            self.rooms_filter["room__queue__sector__project"] = filters.project

    def _filter_agents(self, filters):
        if filters.agent:
            self.rooms_filter["room__user"] = filters.agent

    def division_data(self, filters):
        tz = filters.project.timezone

        self._filter_date_range(filters, tz)
        self._filter_sector(filters)
        self._filter_agents(filters)

        room_metric_query = self.model.filter(
            room__queue__sector__in=filters.user_request.manager_sectors()
        )
        print("filtro division", self.rooms_filter)

        sector_query = (
            room_metric_query.filter(**self.rooms_filter)
            .values(f"{self.division_level}__uuid")
            .annotate(
                uuid=F(f"{self.division_level}__uuid"),
                name=F(f"{self.division_level}__name"),
                waiting_time=Coalesce(
                    Avg("waiting_time"), 0.0, output_field=FloatField()
                ),
                response_time=Coalesce(
                    Avg("message_response_time"), 0.0, output_field=FloatField()
                ),
                interact_time=Coalesce(
                    Avg("interaction_time"), 0.0, output_field=FloatField()
                ),
            )
            .values("uuid", "name", "waiting_time", "response_time", "interact_time")
        )
        print(type(filters))
        print(filters)

        a = QueueRoomsRepository()
        b = ActiveChatsRepository()
        c = ClosedRoomsRepository()
        sectors = [
            Sector(
                uuid=str(sector["uuid"]),
                name=sector["name"],
                waiting_time=sector["waiting_time"],
                response_time=sector["response_time"],
                interact_time=sector["interact_time"],
                active_rooms=sum(
                    map(
                        lambda room: room.active_rooms,
                        ActiveChatsRepository.active_chats(
                            b, filters.set_sector(str(sector["uuid"]))
                        ),
                    )
                ),
                queue_rooms=sum(
                    map(
                        lambda room: room.queue_rooms,
                        QueueRoomsRepository.queue_rooms(
                            a, filters.set_sector(str(sector["uuid"]))
                        ),
                    )  # type: ignore
                ),
                closed_rooms=sum(
                    map(
                        lambda room: room.closed_rooms,
                        ClosedRoomsRepository.closed_rooms(
                            c, filters.set_sector(str(sector["uuid"]))
                        ),
                    )  # type: ignore
                ),
            )
            for sector in sector_query
        ]

        return sectors


class ORMRoomsDataRepository(RoomsDataRepository):
    def __init__(self) -> None:
        self.model = Room.objects.exclude(queue__is_deleted=True)
        self.rooms_filter = {}
        self.rooms_filter["user__isnull"] = False

    def _filter_date_range(self, filters, tz):
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        if filters.start_date and filters.end_date:
            start_time = pendulum_parse(filters.start_date, tzinfo=tz)
            end_time = pendulum_parse(filters.end_date + " 23:59:59", tzinfo=tz)
            self.rooms_filter["created_on__range"] = [start_time, end_time]
        else:
            self.rooms_filter["created_on__gte"] = initial_datetime

    def _filter_agents(self, filters):
        if filters.agent:
            self.rooms_filter["user"] = filters.agent

    def _filter_sector(self, filters):
        if filters.sector:
            self.rooms_filter["queue__sector"] = filters.sector
            if filters.tag:
                self.rooms_filter["tags__uuid"] = filters.tag
        else:
            self.rooms_filter["queue__sector__project"] = filters.project

    def get_cache_key(self, filters):
        DASHBOARD_ROOMS_CACHE_KEY = "dashboard:{filter}:{metric}"

        tz = filters.project.timezone

        self._filter_date_range(filters, tz)
        self._filter_agents(filters)
        self._filter_sector(filters)

        cache_key = DASHBOARD_ROOMS_CACHE_KEY.format(
            filter=parse.urlencode(self.rooms_filter), metric="rooms_metrics"
        )
        return cache_key

    def get_rooms_data(self, filters):
        tz = filters.project.timezone

        self._filter_date_range(filters, tz)
        self._filter_agents(filters)
        self._filter_sector(filters)

        interact_time_agg = Avg("metric__interaction_time")
        message_response_time_agg = Avg("metric__message_response_time")
        waiting_time_agg = Avg("metric__waiting_time")

        if filters.user_request:
            rooms_query = self.model.filter(
                queue__sector__in=filters.user_request.manager_sectors()
            )
            print("filtro general", self.rooms_filter)
            general_data = rooms_query.filter(**self.rooms_filter).aggregate(
                interact_time=interact_time_agg,
                response_time=message_response_time_agg,
                waiting_time=waiting_time_agg,
            )
            return general_data


class RoomsCacheRepository(CacheRepository):
    def get(self, key: str, default=None):
        with get_redis_connection() as redis_connection:
            try:
                redis_general_time_value = redis_connection.get(key)
                rooms_data = json.loads(redis_general_time_value)
                return rooms_data
            except (json.JSONDecodeError, TypeError):
                return default

    def set(self, key, data):
        with get_redis_connection() as redis_connection:
            serialized_data = json.dumps(data)
            redis_connection.set(key, serialized_data, settings.CHATS_CACHE_TIME)
