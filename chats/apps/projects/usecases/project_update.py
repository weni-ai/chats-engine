from dataclasses import dataclass, field
from typing import Optional

from django.db import transaction

from chats.apps.sectors.utils import get_country_from_timezone

from ..models import Project


@dataclass
class ProjectUpdateDTO:
    project_uuid: str
    user_email: str
    name: Optional[str] = None
    timezone: Optional[str] = None
    date_format: Optional[str] = None
    config: Optional[dict] = field(default=None)


class ProjectUpdateUseCase:
    def update_project(self, project_dto: ProjectUpdateDTO) -> Project:
        project = Project.objects.get(uuid=project_dto.project_uuid)

        update_fields = []
        country_changed = False

        if project_dto.name is not None:
            project.name = project_dto.name
            update_fields.append("name")

        if project_dto.timezone is not None:
            old_country = get_country_from_timezone(str(project.timezone))
            new_country = get_country_from_timezone(str(project_dto.timezone))
            country_changed = old_country != new_country
            project.timezone = project_dto.timezone
            update_fields.append("timezone")

        if project_dto.date_format is not None:
            project.date_format = project_dto.date_format
            update_fields.append("date_format")

        if project_dto.config is not None:
            existing_config = project.config or {}
            existing_config.update(project_dto.config)
            project.config = existing_config
            update_fields.append("config")

        if update_fields:
            with transaction.atomic():
                project.save(update_fields=update_fields + ["modified_on"])
                if country_changed:
                    project.delete_sector_holidays()

        return project
