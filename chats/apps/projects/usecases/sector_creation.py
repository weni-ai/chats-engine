from dataclasses import dataclass

from django.contrib.auth import get_user_model

from chats.apps.sectors.models import Sector
from .exceptions import InvalidSectorData

from chats.apps.projects.consumers.sector_consumer import SectorConsumer

from chats.apps.api.v1.dto.sector_dto import SectorDTO
from chats.apps.api.v1.dto.queue_dto import QueueDTO

User = get_user_model()


class SectorCreationUseCase:
    @staticmethod
    def create_sector_dto(message_body):
        sector_dtos = []

        for sector in message_body["sectors"]:
            queues = [
                QueueDTO(uuid=queue["uuid"], name=queue["name"], agents=queue["agents"])
                for queue in sector["queues"]
            ]
            sector_dto = SectorDTO(
                manager_email=sector["manager_email"],
                working_hours=sector["working_hours"],
                service_limit=sector["service_limit"],
                tags=sector["tags"],
                name=sector["name"],
                uuid=sector["uuid"],
                queues=queues,
            )
            sector_dtos.append(sector_dto)

        return sector_dtos

    # TODO
    # def create(sector_dtos):
