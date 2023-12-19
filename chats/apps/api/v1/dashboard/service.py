from typing import List

from chats.apps.api.v1.dashboard.serializers import (
    DashboardClosedRoomSerializer,
    DashboardTransferCountSerializer,
    DashboardQueueRoomsSerializer,
)

from .repository import (
    AgentRepository,
    ClosedRoomsRepository,
    TransferCountRepository,
    QueueRoomsRepository,
)

from .dto import Agent, Filters


class AgentsService:
    def get_agents_data(self, filters: Filters, project) -> List[Agent]:
        agents_repository = AgentRepository()
        return agents_repository.get_agents_data(filters, project)


class RawDataService:
    def get_raw_data(self, filters: Filters):
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

        serialized_agents = closed_rooms_count.data
        serialized_transfer_count = transfer_count.data
        serialized_queue_rooms = queue_rooms_count.data

        combined_data = {
            "raw_data": [
                {
                    "closed_rooms": serialized_agents[0]["closed_rooms"],
                    "transfer_count": serialized_transfer_count[0]["transfer_count"],
                    "queue_rooms": serialized_queue_rooms[0]["queue_rooms"],
                }
            ]
        }

        return combined_data
