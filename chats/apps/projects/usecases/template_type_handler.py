from chats.apps.projects.models import TemplateType
from chats.apps.projects.usecases.exceptions import InvalidTemplateTypeData
from chats.apps.sectors.models import Sector


class TemplateTypeHandler:
    def __init__(self, action: str, config: dict) -> None:
        self.action = action
        self.config = config

    def execute(self):
        return getattr(self, self.action)()

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

    def update(self) -> TemplateType:
        return self.create()

    def delete(self) -> None:
        uuid = self.config.get("uuid")
        try:
            template = TemplateType.objects.get(pk=uuid)
        except TemplateType.DoesNotExist:
            raise InvalidTemplateTypeData(f"The TemplateType {uuid} does not exist!")

        template.delete()

        return
