from typing import List

from django.db.models import Avg

from chats.apps.api.utils import create_room_dto
from chats.apps.api.v1.dashboard.interfaces import CacheRepository, RoomsDataRepository
from chats.apps.api.v1.dashboard.serializers import (
    DashboardActiveRoomsSerializer,
    DashboardClosedRoomSerializer,
    DashboardQueueRoomsSerializer,
    DashboardRoomSerializer,
    DashboardTransferCountSerializer,
)

from .dto import Agent, Filters, Sector
from .repository import (
    ActiveChatsRepository,
    AgentRepository,
    ClosedRoomsRepository,
    QueueRoomsRepository,
    SectorRepository,
    TransferCountRepository,
)


class AgentsService:
    def get_agents_data(self, filters: Filters, project) -> List[Agent]:
        agents_repository = AgentRepository()
        return agents_repository.get_agents_data(filters, project)


class RawDataService:
    def get_raw_data(self, filters: Filters):
        active_rooms_repository = ActiveChatsRepository()
        active_rooms_data = active_rooms_repository.active_chats(filters)
        active_rooms_count = DashboardActiveRoomsSerializer(
            active_rooms_data, many=True
        )

        closed_rooms_repository = ClosedRoomsRepository()
        closed_rooms_data = closed_rooms_repository.closed_rooms(filters)
        closed_rooms_count = DashboardClosedRoomSerializer(closed_rooms_data, many=True)

        transfer_count_repository = TransferCountRepository()
        transfer_count_data = transfer_count_repository.transfer_count(filters)
        transfer_count = DashboardTransferCountSerializer(
            transfer_count_data, many=True
        )

        queue_rooms_repository = QueueRoomsRepository()
        queue_rooms_data = queue_rooms_repository.queue_rooms(filters)
        queue_rooms_count = DashboardQueueRoomsSerializer(queue_rooms_data, many=True)

        serialized_active_rooms = active_rooms_count.data
        serialized_closed_rooms = closed_rooms_count.data
        serialized_transfer_count = transfer_count.data
        serialized_queue_rooms = queue_rooms_count.data

        combined_data = {
            "raw_data": [
                {
                    "active_rooms": serialized_active_rooms[0]["active_rooms"],
                    "closed_rooms": serialized_closed_rooms[0]["closed_rooms"],
                    "transfer_count": serialized_transfer_count[0]["transfer_count"],
                    "queue_rooms": serialized_queue_rooms[0]["queue_rooms"],
                }
            ]
        }

        return combined_data


class SectorService:
    def get_sector_data(self, filters: Filters) -> List[Sector]:
        sectors_repository = SectorRepository()
        return sectors_repository.division_data(filters)


class RoomsDataService:
    def __init__(
        self,
        rooms_data_repository: RoomsDataRepository,
        rooms_cache_repository: CacheRepository,
    ):
        self.rooms_data_repository = rooms_data_repository
        self.rooms_cache_repository = rooms_cache_repository

    def get_rooms_data(self, filters: Filters) -> List[DashboardRoomSerializer]:
        get_cache_key = self.rooms_data_repository.get_cache_key(filters)
        get_cached_data = self.rooms_cache_repository.get(get_cache_key)

        if get_cached_data:
            return get_cached_data

        rooms_data = self.rooms_data_repository.get_rooms_data(filters)
        rooms_dto = create_room_dto(rooms_data)

        self.rooms_cache_repository.set(
            get_cache_key,
            rooms_dto,
        )
        return rooms_dto


class TimeMetricsService:
    def get_time_metrics(self, filters: Filters, project):
        import pendulum
        import pytz
        from django.db.models import Q
        from django.utils import timezone

        from chats.apps.dashboard.utils import calculate_last_queue_waiting_time
        from chats.apps.rooms.models import Room

        tz = pytz.timezone(str(project.timezone))
        rooms_filter = Q(queue__sector__project=project)

        if filters.start_date and filters.end_date:
            start_time = pendulum.parse(filters.start_date).replace(tzinfo=tz)
            end_time = pendulum.parse(filters.end_date + " 23:59:59").replace(tzinfo=tz)
            rooms_filter &= Q(created_on__range=[start_time, end_time])
        else:
            initial_datetime = (
                timezone.now()
                .astimezone(tz)
                .replace(hour=0, minute=0, second=0, microsecond=0)
            )
            rooms_filter &= Q(created_on__gte=initial_datetime)

        if filters.agent:
            rooms_filter &= Q(user=filters.agent)

        if filters.sector:
            rooms_filter &= Q(queue__sector=filters.sector)
            if filters.tag:
                rooms_filter &= Q(tags__uuid=filters.tag)

        if filters.queue:
            rooms_filter &= Q(queue__uuid=filters.queue)

        waiting_filter = Q(
            queue__sector__project=project,
            is_active=True,
            user__isnull=True,
            added_to_queue_at__isnull=False,
        )

        if filters.sector:
            waiting_filter &= Q(queue__sector=filters.sector)
            if filters.tag:
                waiting_filter &= Q(tags__uuid=filters.tag)
        if filters.queue:
            waiting_filter &= Q(queue__uuid=filters.queue)

        active_rooms_in_queue = Room.objects.filter(waiting_filter)

        waiting_times = []
        for room in active_rooms_in_queue:
            waiting_time = calculate_last_queue_waiting_time(room)
            waiting_times.append(waiting_time)

        avg_waiting_time = (
            int(sum(waiting_times) / len(waiting_times)) if waiting_times else 0
        )
        max_waiting_time = int(max(waiting_times)) if waiting_times else 0

        first_response_times = []

        try:
            rooms_with_saved_response = Room.objects.filter(
                queue__sector__project=project,
                is_active=True,
                user__isnull=False,
                metric__isnull=False,
                metric__first_response_time__gt=0,
                queue__is_deleted=False,
                queue__sector__is_deleted=False,
            ).select_related("metric")

            if filters.sector:
                rooms_with_saved_response = rooms_with_saved_response.filter(
                    queue__sector=filters.sector
                )
                if filters.tag:
                    rooms_with_saved_response = rooms_with_saved_response.filter(
                        tags__uuid=filters.tag
                    )
            if filters.queue:
                rooms_with_saved_response = rooms_with_saved_response.filter(
                    queue__uuid=filters.queue
                )
            if filters.agent:
                rooms_with_saved_response = rooms_with_saved_response.filter(
                    user=filters.agent
                )

            for room in rooms_with_saved_response:
                first_response_times.append(room.metric.first_response_time)
        except Exception:
            pass

        try:
            rooms_waiting_response = Room.objects.filter(
                queue__sector__project=project,
                is_active=True,
                user__isnull=False,
                first_user_assigned_at__isnull=False,
                queue__is_deleted=False,
                queue__sector__is_deleted=False,
            ).filter(Q(metric__isnull=True) | Q(metric__first_response_time=0))

            if filters.sector:
                rooms_waiting_response = rooms_waiting_response.filter(
                    queue__sector=filters.sector
                )
                if filters.tag:
                    rooms_waiting_response = rooms_waiting_response.filter(
                        tags__uuid=filters.tag
                    )
            if filters.queue:
                rooms_waiting_response = rooms_waiting_response.filter(
                    queue__uuid=filters.queue
                )
            if filters.agent:
                rooms_waiting_response = rooms_waiting_response.filter(
                    user=filters.agent
                )

            for room in rooms_waiting_response:
                has_any_agent_messages = (
                    room.messages.filter(user__isnull=False)
                    .exclude(automatic_message__isnull=False)
                    .exists()
                )

                if has_any_agent_messages:
                    continue

                time_waiting = int(
                    (timezone.now() - room.first_user_assigned_at).total_seconds()
                )
                first_response_times.append(time_waiting)

        except Exception:
            pass

        avg_first_response_time = (
            int(sum(first_response_times) / len(first_response_times))
            if first_response_times
            else 0
        )
        max_first_response_time = (
            int(max(first_response_times)) if first_response_times else 0
        )

        active_conversation_filter = Q(
            queue__sector__project=project,
            is_active=True,
            user__isnull=False,
            first_user_assigned_at__isnull=False,
            queue__is_deleted=False,
            queue__sector__is_deleted=False,
        )

        if filters.agent:
            active_conversation_filter &= Q(user=filters.agent)
        if filters.sector:
            active_conversation_filter &= Q(queue__sector=filters.sector)
            if filters.tag:
                active_conversation_filter &= Q(tags__uuid=filters.tag)
        if filters.queue:
            active_conversation_filter &= Q(queue__uuid=filters.queue)

        active_rooms_with_user = Room.objects.filter(active_conversation_filter)

        conversation_durations = []
        for room in active_rooms_with_user:
            duration = (timezone.now() - room.first_user_assigned_at).total_seconds()
            conversation_durations.append(int(duration))

        avg_conversation_duration = (
            int(sum(conversation_durations) / len(conversation_durations))
            if conversation_durations
            else 0
        )
        max_conversation_duration = (
            int(max(conversation_durations)) if conversation_durations else 0
        )

        result = {
            "avg_waiting_time": avg_waiting_time,
            "max_waiting_time": max_waiting_time,
            "avg_first_response_time": avg_first_response_time,
            "max_first_response_time": max_first_response_time,
            "avg_conversation_duration": avg_conversation_duration,
            "max_conversation_duration": max_conversation_duration,
        }

        if filters.start_date and filters.end_date:
            closed_rooms_filter = rooms_filter & Q(is_active=False)

            avg_message_response_time = (
                Room.objects.filter(closed_rooms_filter)
                .filter(metric__isnull=False, metric__message_response_time__gt=0)
                .aggregate(avg=Avg("metric__message_response_time"))["avg"]
            )

            result["avg_message_response_time"] = (
                int(avg_message_response_time) if avg_message_response_time else 0
            )

        return result
