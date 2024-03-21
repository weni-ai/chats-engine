from dataclasses import dataclass

from django.contrib.auth import get_user_model

from ..models import ProjectPermission

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

    def get_or_create_user_by_email(self, email: str) -> tuple:
        return User.objects.get_or_create(email=email)

    def edit_permission(self, project_permission: ProjectPermission, user, role_value):
        project_permission.project = self.config.get("project")
        project_permission.user = user
        project_permission.role = role_value
        project_permission.save()

    def create_permission(self, project_permission_dto: ProjectPermissionDTO):
        user, _ = self.get_or_create_user_by_email(project_permission_dto.user)
        role_value = self.role_mapping()

        project_permission = ProjectPermission.objects.get(
            project=project_permission_dto.project,
            user=project_permission_dto.user,
            default=None,
        )

        if project_permission is not None:
            self.edit_permission(project_permission, user, role_value)

        project_permission = ProjectPermission.objects.create(
            project=project_permission_dto.project,
            user=project_permission_dto.user,
            role=role_value,
        )

    def delete_permission(self, project_permission_dto: ProjectPermissionDTO):
        # verificar se a permissão existe antes de deletar
        project_permission = ProjectPermission.objects.get(
            project=project_permission_dto.project,
            user=project_permission_dto.user,
        )
        project_permission.delete()
