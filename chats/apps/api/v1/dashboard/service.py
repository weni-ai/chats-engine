from typing import List

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
        from chats.apps.rooms.models import Room
        import pytz
        
        self.project = project
        self.filters = filters
        self.tz = pytz.timezone(str(project.timezone))
        
        waiting_metrics = self._calculate_waiting_time_metrics(Room)
        first_response_metrics = self._calculate_first_response_metrics(Room)
        conversation_metrics = self._calculate_conversation_duration_metrics(Room)
        
        return {
            "avg_waiting_time": waiting_metrics["avg"],
            "max_waiting_time": waiting_metrics["max"],
            "avg_first_response_time": first_response_metrics["avg"],
            "max_first_response_time": first_response_metrics["max"],
            "avg_conversation_duration": conversation_metrics["avg"],
            "max_conversation_duration": conversation_metrics["max"],
        }
    
    def _build_base_filter(self, **additional_filters):
        from django.db.models import Q
        
        base_filter = Q(
            queue__sector__project=self.project,
            **additional_filters
        )
        return base_filter
    
    def _apply_optional_filters(self, base_filter):
        from django.db.models import Q
        
        filters = self.filters
        
        if filters.agent:
            base_filter &= Q(user=filters.agent)
        
        if filters.sector:
            base_filter &= Q(queue__sector=filters.sector)
            if filters.tag:
                base_filter &= Q(tags__uuid=filters.tag)
        
        if filters.queue:
            base_filter &= Q(queue__uuid=filters.queue)
        
        return base_filter
    
    def _calculate_waiting_time_metrics(self, Room):
        from chats.apps.dashboard.utils import calculate_last_queue_waiting_time
        
        waiting_filter = self._build_base_filter(
            is_active=True,
            user__isnull=True,
            added_to_queue_at__isnull=False,
        )
        waiting_filter = self._apply_optional_filters(waiting_filter)
        
        active_rooms_in_queue = Room.objects.filter(waiting_filter)
        waiting_times = [
            calculate_last_queue_waiting_time(room)
            for room in active_rooms_in_queue
        ]
        
        return self._calculate_avg_and_max(waiting_times)
    
    def _calculate_first_response_metrics(self, Room):
        saved_times = self._get_saved_first_response_times(Room)
        pending_times = self._get_pending_first_response_times(Room)
        
        all_times = saved_times + pending_times
        return self._calculate_avg_and_max(all_times)
    
    def _get_saved_first_response_times(self, Room):
        try:
            base_filter = self._build_base_filter(
                is_active=True,
                user__isnull=False,
                metric__isnull=False,
                metric__first_response_time__gt=0,
                queue__is_deleted=False,
                queue__sector__is_deleted=False,
            )
            rooms_filter = self._apply_optional_filters(base_filter)
            
            rooms = Room.objects.filter(rooms_filter).select_related("metric")
            return [room.metric.first_response_time for room in rooms]
        except Exception:
            return []
    
    def _get_pending_first_response_times(self, Room):
        from django.db.models import Q
        from django.utils import timezone
        
        try:
            base_filter = self._build_base_filter(
                is_active=True,
                user__isnull=False,
                first_user_assigned_at__isnull=False,
                queue__is_deleted=False,
                queue__sector__is_deleted=False,
            )
            base_filter &= (Q(metric__isnull=True) | Q(metric__first_response_time=0))
            rooms_filter = self._apply_optional_filters(base_filter)
            
            rooms = Room.objects.filter(rooms_filter)
            
            pending_times = []
            for room in rooms:
                if self._has_agent_messages(room):
                    continue
                
                time_waiting = int(
                    (timezone.now() - room.first_user_assigned_at).total_seconds()
                )
                pending_times.append(time_waiting)
            
            return pending_times
        except Exception:
            return []
    
    def _has_agent_messages(self, room):
        return (
            room.messages.filter(user__isnull=False)
            .exclude(automatic_message__isnull=False)
            .exists()
        )
    
    def _calculate_conversation_duration_metrics(self, Room):
        from django.utils import timezone
        
        active_filter = self._build_base_filter(
            is_active=True,
            user__isnull=False,
            first_user_assigned_at__isnull=False,
            queue__is_deleted=False,
            queue__sector__is_deleted=False,
        )
        active_filter = self._apply_optional_filters(active_filter)
        
        active_rooms = Room.objects.filter(active_filter)
        durations = [
            int((timezone.now() - room.first_user_assigned_at).total_seconds())
            for room in active_rooms
        ]
        
        return self._calculate_avg_and_max(durations)
    
    def _calculate_avg_and_max(self, values):
        if not values:
            return {"avg": 0, "max": 0}
        
        return {
            "avg": int(sum(values) / len(values)),
            "max": int(max(values))
        }
