from django.contrib.auth import get_user_model

from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector, SectorTag
from chats.apps.feature_version.models import IntegratedFeature

from chats.apps.api.v1.dto.sector_dto import SectorDTO, dto_to_dict
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
                QueueDTO(uuid=queue["uuid"], name=queue["name"])
                for queue in sector["queues"]
            ]
            sector_dto = SectorDTO(
                working_hours=sector["working_hours"],
                service_limit=sector["service_limit"],
                tags=sector["tags"],
                name=sector["name"],
                uuid=sector["uuid"],
                queues=queues,
            )
            sector_dtos.append(sector_dto)

        return sector_dtos

    def integrate_feature(self, body, sector_dtos):
        for sector in sector_dtos:
            project = Project.objects.get(pk=body["project_uuid"])
            created_sector = Sector.objects.create(
                name=sector.name,
                project=project,
                rooms_limit=sector.service_limit,
                work_start=sector.working_hours["init"],
                work_end=sector.working_hours["close"],
            )
            sector.uuid = str(created_sector.uuid)

            for tag in sector.tags:
                SectorTag.objects.create(name=tag, sector=created_sector)

            content = {
                "project_uuid": str(created_sector.project.uuid),
                "name": created_sector.name,
                "project_auth": str(created_sector.external_token.pk),
                "user_email": str(body["user_email"]),
                "uuid": str(created_sector.uuid),
                "queues": [],
            }
            for queue in sector.queues:
                created_queue = Queue.objects.create(
                    sector=created_sector,
                    name=queue.name,
                )
                queue.uuid = str(created_queue.uuid)

                content["queues"].append(
                    {"uuid": str(created_queue.uuid), "name": created_queue.name}
                )

            self._flows_client.request_ticketer(content=content)

    def create_integrated_feature_object(self, body, sector_dtos):
        sector_dicts = [dto_to_dict(dto) for dto in sector_dtos]
        project = Project.objects.get(pk=body["project_uuid"])

        IntegratedFeature.objects.create(
            project=project,
            feature=body["feature_uuid"],
            current_version=sector_dicts,
        )
