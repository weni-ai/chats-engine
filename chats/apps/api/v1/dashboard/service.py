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
