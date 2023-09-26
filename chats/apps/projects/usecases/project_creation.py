from dataclasses import dataclass

from django.contrib.auth import get_user_model

from ..models import Project, ProjectPermission, TemplateType
from .exceptions import InvalidProjectData

User = get_user_model()


@dataclass
class ProjectCreationDTO:
    uuid: str
    name: str
    is_template: bool
    user_email: str
    date_format: str
    timezone: str
    template_type_uuid: str
    authorizations: list


class ProjectCreationUseCase:
    def __init__(self, sector_setup_handler):
        self.__sector_setup_handler = sector_setup_handler

    def get_or_create_user_by_email(self, email: str) -> tuple:
        return User.objects.get_or_create(email=email)

    def create_project(self, project_dto: ProjectCreationDTO):
        project: Project = None
        template_type: TemplateType = None

        if project_dto.is_template and project_dto.template_type_uuid is None:
            raise InvalidProjectData(
                "'template_type_uuid' cannot be empty when 'is_template' is True!"
            )

        if project_dto.is_template:
            try:
                template_type = TemplateType.objects.get(
                    uuid=project_dto.template_type_uuid
                )
            except TemplateType.DoesNotExist:
                raise InvalidProjectData(
                    f"Template Type with uuid `{project_dto.template_type_uuid}` does not exists!"
                )

        user, _ = self.get_or_create_user_by_email(project_dto.user_email)

        if Project.objects.filter(uuid=project_dto.uuid).exists():
            raise InvalidProjectData(f"The project `{project_dto.uuid}` already exist!")

        project = Project.objects.create(
            uuid=project_dto.uuid,
            name=project_dto.name,
            is_template=project_dto.is_template,
            date_format=project_dto.date_format,
            timezone=project_dto.timezone,
        )

        creator_permission, _ = ProjectPermission.objects.get_or_create(
            user=user, project=project, role=1
        )

        for permission in project_dto.authorizations:
            permission_user = User.objects.get_or_create(
                email=permission.get("user_email")
            )[0]
            project.permissions.get_or_create(
                user=permission_user,
                defaults={"role": 1 if permission.get("role") == 3 else 2},
            )

        if project_dto.is_template:
            self.__sector_setup_handler.setup_sectors_in_project(
                project, template_type, creator_permission
            )
            project.template_type = template_type
            project.save()
