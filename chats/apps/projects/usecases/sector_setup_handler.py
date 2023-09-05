from chats.apps.api.v1.internal.eda_clients.flows_eda_client import FlowsEDAClient
from chats.apps.projects.models import Project, ProjectPermission, TemplateType
from chats.apps.queues.models import QueueAuthorization
from chats.apps.sectors.models import SectorAuthorization

from .exceptions import InvalidTemplateTypeData


class SectorSetupHandlerUseCase:
    def __init__(self):
        self._flows_client = FlowsEDAClient()

    def setup_sectors_in_project(
        self,
        project: Project,
        template_type: TemplateType,
        permission: ProjectPermission,
    ):
        setup = template_type.setup
        if setup == {}:
            raise InvalidTemplateTypeData(
                f"The `setup` of TemplateType {template_type.uuid} is empty!"
            )

        for setup_sector in setup.get("sectors"):
            setup_queues = setup_sector.pop("queues", None)

            if not setup_queues:
                continue

            sector, created = project.sectors.get_or_create(
                name=setup_sector.pop("name"), defaults=setup_sector
            )
            if not created:
                continue

            SectorAuthorization.objects.create(
                role=1, permission=permission, sector=sector
            )
            content = {
                "project_uuid": str(project.uuid),
                "name": sector.name,
                "project_auth": str(permission.pk),
                "uuid": str(sector.uuid),
                "queues": [],
            }

            for setup_queue in setup_queues:
                queue = sector.queues.get_or_create(
                    name=setup_queue.pop("name"), defaults=setup_queue
                )[0]
                QueueAuthorization.objects.create(
                    role=1, permission=permission, queue=queue
                )
                content["queues"].append({"uuid": str(queue.uuid), "name": queue.name})

            self._flows_client.request_ticketer(content=content)
