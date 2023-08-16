from chats.apps.api.v1.internal.eda_clients.flows_eda_client import FlowsEDAClient
from chats.apps.projects.models import Project, ProjectPermission, TemplateType

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
        action = "create"
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
            self._flows_client.request_ticketer(
                action=action,
                content={
                    "project_uuid": str(project.uuid),
                    "name": sector.name,
                    "config": {
                        "project_auth": str(permission.pk),
                        "sector_uuid": str(sector.uuid),
                    },
                },
            )

            for setup_queue in setup_queues:
                queue = sector.queues.get_or_create(
                    name=setup_queue.pop("name"), defaults=setup_queue
                )[0]
                self._flows_client.request_queue(
                    action=action,
                    content={
                        "sector_uuid": str(queue.sector.uuid),
                        "uuid": str(queue.uuid),
                        "name": queue.name,
                    },
                )
