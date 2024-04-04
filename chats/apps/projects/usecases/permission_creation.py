from dataclasses import dataclass

from django.contrib.auth import get_user_model

from ..models import ProjectPermission, Project

from chats.apps.projects.usecases import InvalidProjectPermission

from ..models import Project, ProjectPermission

User = get_user_model()


@dataclass
class ProjectPermissionDTO:
    project: str
    user: str
    role: str


class ProjectPermissionCreationUseCase:
    def __init__(self, config: dict) -> None:
        self.config = config

    def role_mapping(self):
        return 1 if self.config.get("role") == 3 else 2

    def get_project(self):
        return Project.objects.get(uuid=self.config.get("project"))

    def get_or_create_user_by_email(self, email: str) -> tuple:
        return User.objects.get_or_create(email=email)

    def edit_permission(
        self, project_permission: ProjectPermission, user, role_value, project
    ):
        project_permission.project = project
        project_permission.user = user
        project_permission.role = role_value
        project_permission.save()

    def create_permission(self, project_permission_dto: ProjectPermissionDTO):
        user, _ = self.get_or_create_user_by_email(project_permission_dto.user)
        role_value = self.role_mapping()
        project = self.get_project()

        project_permission, created = ProjectPermission.objects.get_or_create(
            project=project, user=user, defaults={"role": role_value}
        )

        if not created:
            self.edit_permission(project_permission, user, role_value, project)

    def delete_permission(self, project_permission_dto: ProjectPermissionDTO):
        try:
            project_permission = ProjectPermission.objects.get(
                project=project_permission_dto.project,
                user=project_permission_dto.user,
            )
        except Exception as err:
            raise InvalidProjectPermission(err)

        project_permission.delete()
