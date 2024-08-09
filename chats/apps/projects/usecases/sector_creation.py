from dataclasses import dataclass

from django.contrib.auth import get_user_model

from chats.apps.projects.models.models import ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector, SectorAuthorization
from .exceptions import InvalidSectorData

from chats.apps.projects.consumers.sector_consumer import SectorConsumer

from chats.apps.api.v1.dto.sector_dto import SectorDTO
from chats.apps.api.v1.dto.queue_dto import QueueDTO

from chats.apps.api.v1.internal.eda_clients.flows_eda_client import FlowsEDAClient

User = get_user_model()


class SectorCreationUseCase:
    def __init__(self):
        self._flows_client = FlowsEDAClient()

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

    def create(self, body, sector_dtos):
        for sector in sector_dtos:
            created_sector = Sector.objects.create(
                uuid=sector.uuid,
                name=sector.name,
                project=body["project"],
                rooms_limit=sector.service_limit,
                work_start=sector.working_hours["init"],
                work_end=sector.working_hours["close"],
            )
            for manager in sector.manager_email:
                manager_permission = ProjectPermission.objects.get(email=manager)
                SectorAuthorization.objects.create(
                    role=1, permission=manager_permission, sector=created_sector
                )

            for queue in sector.queues:
                created_queue = Queue.objects.create(
                    sector=created_sector,
                    name=queue.name,
                    uuid=queue.uuid,
                )

                for agent in queue.agents:
                    agent_permission = ProjectPermission.objects.get(email=agent)
                    QueueAuthorization.objects.create(
                        role=1,
                        permission=agent_permission,
                        queue=created_queue,
                    )
            content = {
                "project_uuid": str(created_sector.project),
                "name": created_sector.name,
                "project_auth": str(created_sector.external_token.pk),
                "user_email": str(body["user_email"]),
                "uuid": str(created_sector.uuid),
                "queues": [],
            }
            self._flows_client.request_ticketer(content=content)