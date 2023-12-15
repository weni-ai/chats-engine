from typing import List

from pendulum.parser import parse as pendulum_parse

from django.db.models import Count, OuterRef, Q, Subquery, Sum
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.projects.models import ProjectPermission
from .dto import Agent, Filters, ClosedRoomData, TransferRoomData, QueueRoomData
from chats.apps.rooms.models import Room


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
            self.rooms_filter["queue__sector"] = filters.get("sector")
            if filters.tag:
                self.rooms_filter["tags__uuid"] = filters.get("tag")
            if filters.queue:
                self.rooms_filter["queue"] = filters.get("queue")
            return self.rooms_filter

        self.rooms_filter["queue__sector__project"] = filters.project
        return self.rooms_filter

    def _filter_agents(self, filters):
        if filters.agent:
            self.rooms_filter["user"] = filters.get("agent")
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
            self.rooms_filter["queue__sector"] = filters.get("sector")
            if filters.tag:
                self.rooms_filter["tags__uuid"] = filters.get("tag")
            if filters.queue:
                self.rooms_filter["queue"] = filters.get("queue")
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
            self.rooms_filter["queue__sector"] = filters.get("sector")
            return self.rooms_filter

        self.rooms_filter["queue__sector__project"] = filters.project
        return self.rooms_filter

    def queue_rooms(self, filters):
        tz = filters.project.timezone

        self._filter_date_range(filters, tz)
        self._filter_sector(filters)
        queue_rooms = []
        if filters.user_request:
            rooms_query = self.model.filter(
                queue__sector__in=filters.user_request.manager_sectors()
            )

            queue_rooms_metric = rooms_query.filter(**self.rooms_filter).count()
            queue_rooms = [QueueRoomData(queue_rooms=queue_rooms_metric)]
            return queue_rooms

        return queue_rooms
