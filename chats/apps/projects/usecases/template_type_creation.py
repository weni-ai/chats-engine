from chats.apps.projects.models import Project, TemplateType
from chats.apps.sectors.models import Sector


def create_template_type(uuid: str, project_uuid: Project, name: str) -> TemplateType:
    setup = {
        "sectors": [
            sector.template_type_setup
            for sector in Sector.objects.filter(project=project_uuid, is_deleted=False)
        ]
    }

    template_type = TemplateType.objects.update_or_create(
        uuid=uuid, defaults=dict(name=name, setup=setup)
    )[0]

    return template_type
