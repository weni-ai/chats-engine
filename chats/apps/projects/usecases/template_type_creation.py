from chats.apps.projects.models import TemplateType
from chats.apps.sectors.models import Sector
from chats.apps.projects.models import Project
from chats.apps.projects.usecases import InvalidTemplateTypeData


class TemplateTypeCreation:
    def __init__(self, config: dict) -> None:
        self.config = config

    def create(self) -> TemplateType:
        try:
            Project.objects.get(uuid=self.config.get("project_uuid"))
        except Exception as err:
            raise InvalidTemplateTypeData(err)

        setup = {
            "sectors": [
                sector.template_type_setup
                for sector in Sector.objects.filter(
                    project=self.config.get("project_uuid"), is_deleted=False
                )
            ]
        }

        template_type = TemplateType.objects.update_or_create(
            uuid=self.config.get("uuid"),
            defaults=dict(name=self.config.get("name"), setup=setup),
        )[0]

        return template_type
