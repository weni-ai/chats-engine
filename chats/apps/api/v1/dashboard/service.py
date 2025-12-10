from typing import List

from django.db.models import Avg, Max, Q
from django.utils import timezone

from chats.apps.api.utils import create_room_dto
from chats.apps.api.v1.dashboard.interfaces import CacheRepository, RoomsDataRepository
from chats.apps.api.v1.dashboard.serializers import (
    DashboardActiveRoomsSerializer,
    DashboardClosedRoomSerializer,
    DashboardQueueRoomsSerializer,
    DashboardRoomSerializer,
    DashboardTransferCountSerializer,
)
from chats.apps.dashboard.utils import calculate_last_queue_waiting_time
from chats.apps.rooms.models import Room

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
    def _normalize_to_list(self, value):
        """Ensure value is a list."""
        if value is None:
            return None
        return value if isinstance(value, list) else [value]

    def _apply_room_filters(self, queryset, filters: Filters):
        """Apply common filters to a queryset."""
        if filters.sector:
            queryset = queryset.filter(queue__sector__in=filters.sector)
            if filters.tag:
                queryset = queryset.filter(tags__uuid__in=filters.tag)
        if filters.queue:
            queryset = queryset.filter(queue__uuid__in=filters.queue)
        if filters.agent:
            queryset = queryset.filter(user=filters.agent)
        return queryset

    def _apply_q_filters(self, base_filter: Q, filters: Filters) -> Q:
        """Apply common Q filters."""
        if filters.sector:
            base_filter &= Q(queue__sector__in=filters.sector)
            if filters.tag:
                base_filter &= Q(tags__uuid__in=filters.tag)
        if filters.queue:
            base_filter &= Q(queue__uuid__in=filters.queue)
        if filters.agent:
            base_filter &= Q(user=filters.agent)
        return base_filter

    def _calculate_avg_max(self, values: list) -> tuple:
        """Calculate average and maximum from a list of values."""
        if not values:
            return 0, 0
        return int(sum(values) / len(values)), int(max(values))

    def _get_waiting_time_metrics(self, filters: Filters, project) -> tuple:
        """Calculate waiting time metrics for rooms in queue."""
        waiting_filter = Q(
            queue__sector__project=project,
            is_active=True,
            user__isnull=True,
            added_to_queue_at__isnull=False,
        )
        if filters.sector:
            waiting_filter &= Q(queue__sector__in=filters.sector)
            if filters.tag:
                waiting_filter &= Q(tags__uuid__in=filters.tag)
        if filters.queue:
            waiting_filter &= Q(queue__uuid__in=filters.queue)

        active_rooms_in_queue = Room.objects.filter(waiting_filter)
        waiting_times = [
            calculate_last_queue_waiting_time(room) for room in active_rooms_in_queue
        ]
        return self._calculate_avg_max(waiting_times)

    def _get_saved_response_times(self, filters: Filters, project) -> list:
        """Get first response times from rooms with saved metrics."""
        try:
            queryset = Room.objects.filter(
                queue__sector__project=project,
                is_active=True,
                user__isnull=False,
                metric__isnull=False,
                metric__first_response_time__gt=0,
                queue__is_deleted=False,
                queue__sector__is_deleted=False,
            ).select_related("metric")
            queryset = self._apply_room_filters(queryset, filters)
            return [room.metric.first_response_time for room in queryset]
        except Exception:
            return []

    def _get_waiting_response_times(self, filters: Filters, project) -> list:
        """Get first response times from rooms waiting for response."""
        try:
            queryset = Room.objects.filter(
                queue__sector__project=project,
                is_active=True,
                user__isnull=False,
                first_user_assigned_at__isnull=False,
                queue__is_deleted=False,
                queue__sector__is_deleted=False,
            ).filter(
                Q(metric__isnull=True)
                | Q(metric__first_response_time=0)
                | Q(metric__first_response_time__isnull=True)
            )
            queryset = self._apply_room_filters(queryset, filters)
            return [
                int((timezone.now() - room.first_user_assigned_at).total_seconds())
                for room in queryset
            ]
        except Exception:
            return []

    def _get_first_response_time_metrics(self, filters: Filters, project) -> tuple:
        """Calculate first response time metrics."""
        first_response_times = []
        first_response_times.extend(self._get_saved_response_times(filters, project))
        first_response_times.extend(self._get_waiting_response_times(filters, project))
        return self._calculate_avg_max(first_response_times)

    def _get_conversation_duration_metrics(self, filters: Filters, project) -> tuple:
        """Calculate conversation duration metrics."""
        active_conversation_filter = Q(
            queue__sector__project=project,
            is_active=True,
            user__isnull=False,
            first_user_assigned_at__isnull=False,
            queue__is_deleted=False,
            queue__sector__is_deleted=False,
        )
        active_conversation_filter = self._apply_q_filters(
            active_conversation_filter, filters
        )
        active_rooms_with_user = Room.objects.filter(active_conversation_filter)
        conversation_durations = [
            int((timezone.now() - room.first_user_assigned_at).total_seconds())
            for room in active_rooms_with_user
        ]
        return self._calculate_avg_max(conversation_durations)

    def _normalize_filters(self, filters: Filters):
        """Normalize filter values to lists."""
        filters.sector = self._normalize_to_list(filters.sector)
        filters.queue = self._normalize_to_list(filters.queue)
        filters.tag = self._normalize_to_list(filters.tag)

    def get_time_metrics(self, filters: Filters, project):
        self._normalize_filters(filters)

        avg_waiting_time, max_waiting_time = self._get_waiting_time_metrics(
            filters, project
        )
        (
            avg_first_response_time,
            max_first_response_time,
        ) = self._get_first_response_time_metrics(filters, project)
        (
            avg_conversation_duration,
            max_conversation_duration,
        ) = self._get_conversation_duration_metrics(filters, project)

        return {
            "avg_waiting_time": avg_waiting_time,
            "max_waiting_time": max_waiting_time,
            "avg_first_response_time": avg_first_response_time,
            "max_first_response_time": max_first_response_time,
            "avg_conversation_duration": avg_conversation_duration,
            "max_conversation_duration": max_conversation_duration,
        }

    def get_time_metrics_for_analysis(self, filters: Filters, project):
        if not filters.start_date and not filters.end_date:
            raise ValueError("Start date and end date are required")

        rooms_filter = (
            Q(queue__sector__project=project)
            & Q(is_active=False)
            & Q(ended_at__gte=filters.start_date)
            & Q(ended_at__lte=filters.end_date)
        )

        if filters.agent:
            rooms_filter &= Q(user=filters.agent)

        if filters.sector:
            if not isinstance(filters.sector, list):
                filters.sector = [filters.sector]
            rooms_filter &= Q(queue__sector__in=filters.sector)

        if filters.queue:
            if not isinstance(filters.queue, list):
                filters.queue = [filters.queue]
            rooms_filter &= Q(queue__uuid__in=filters.queue)

        if filters.tag:
            if not isinstance(filters.tag, list):
                filters.tag = [filters.tag]
            rooms_filter &= Q(tags__uuid__in=filters.tag)

        max_waiting_time = Room.objects.filter(rooms_filter).aggregate(
            Max("metric__waiting_time")
        )["metric__waiting_time__max"]
        avg_waiting_time = Room.objects.filter(rooms_filter).aggregate(
            Avg("metric__waiting_time")
        )["metric__waiting_time__avg"]

        avg_first_response_time = Room.objects.filter(rooms_filter).aggregate(
            Avg("metric__first_response_time")
        )["metric__first_response_time__avg"]
        max_first_response_time = Room.objects.filter(rooms_filter).aggregate(
            Max("metric__first_response_time")
        )["metric__first_response_time__max"]

        avg_conversation_duration = (
            Room.objects.filter(rooms_filter)
            .filter(first_user_assigned_at__isnull=False)
            .aggregate(Avg("metric__interaction_time"))["metric__interaction_time__avg"]
        )
        max_conversation_duration = (
            Room.objects.filter(rooms_filter)
            .filter(first_user_assigned_at__isnull=False)
            .aggregate(Max("metric__interaction_time"))["metric__interaction_time__max"]
        )

        avg_message_response_time = (
            Room.objects.filter(rooms_filter)
            .filter(metric__isnull=False, metric__message_response_time__gt=0)
            .aggregate(avg=Avg("metric__message_response_time"))["avg"]
        )

        return {
            "max_waiting_time": (int(max_waiting_time or 0)),
            "avg_waiting_time": (int(avg_waiting_time or 0)),
            "max_first_response_time": (int(max_first_response_time or 0)),
            "avg_first_response_time": (int(avg_first_response_time or 0)),
            "max_conversation_duration": (int(max_conversation_duration or 0)),
            "avg_conversation_duration": (int(avg_conversation_duration or 0)),
            "avg_message_response_time": (int(avg_message_response_time or 0)),
        }
