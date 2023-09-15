from chats.apps.projects.models import TemplateType
from chats.apps.sectors.models import Sector


class TemplateTypeCreation:
    def __init__(self, config: dict) -> None:
        self.config = config

    def create(self) -> TemplateType:
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
