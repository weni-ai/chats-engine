from django.utils import timezone
from pendulum.parser import parse as pendulum_parse

from chats.apps.projects.models import ProjectPermission
from chats.apps.rooms.models import Room


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
        self.user_request = ProjectPermission.objects.get(
            user=filters.user_request, project=filters.project
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
        if filters.get("sector"):
            self.rooms_filter["queue__sector"] = filters.get("sector")
            if filters.get("tag"):
                self.rooms_filter["tags__uuid"] = filters.get("tag")
            if filters.get("queue"):
                self.rooms_filter["queue"] = filters.get("queue")
            return self.rooms_filter

        self.rooms_filter["queue__sector__project"] = filters.project
        return self.rooms_filter

    def _filter_agents(self, filters):
        if filters.get("agent"):
            self.rooms_filter["user"] = filters.get("agent")
            return self.rooms_filter

    def closed_rooms(self, filters):
        tz = filters.project.timezone

        self._filter_date_range(filters, tz)
        self._filter_sector(filters)
        self._filter_agents(filters)

        if filters.get("user_request"):
            rooms_query = self.model.filter(
                queue__sector__in=self.user_request.manager_sectors()
            )
            closed_rooms = rooms_query.filter(self.rooms_filter).count()
            return closed_rooms

        return {}
