from chats.apps.projects.models import Project, ProjectPermission, TemplateType

from .exceptions import InvalidTemplateTypeData


class SectorSetupHandlerUseCase:
    def __init__(self, connect_client, flows_client):
        self.__connect_client = connect_client
        self.__flows_client = flows_client

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
                raise InvalidTemplateTypeData(
                    f"The TemplateType {template_type.uuid} has an invalid setup!"
                )

            sector, created = project.sectors.get_or_create(
                name=setup_sector.pop("name"), defaults=setup_queues
            )
            if not created:
                continue
            self.__connect_client().create_ticketer(
                project_uuid=str(project.uuid),
                name=sector.name,
                config={
                    "project_auth": str(permission.pk),
                    "sector_uuid": str(sector.uuid),
                },
            )

            for setup_queue in setup_queues:
                queue = sector.queues.get_or_create(
                    name=setup_queue.pop("name"), defaults=setup_queue
                )[0]
                self.__flows_client().create_queue(
                    str(queue.uuid), queue.name, str(queue.sector.uuid)
                )
