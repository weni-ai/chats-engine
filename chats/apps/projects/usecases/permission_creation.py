from dataclasses import dataclass

from django.contrib.auth import get_user_model

from ..models import ProjectPermission
from .exceptions import InvalidProjectPermission

User = get_user_model()


@dataclass
class ProjectPermissionDTO:
    uuid: str
    project: str
    user: str
    role: str


class ProjectPermissionCreationUseCase:
    def __init__(self, config: dict) -> None:
        self.config = config

    def get_or_create_user_by_email(self, email: str) -> tuple:
        return User.objects.get_or_create(email=email)

    def edit_permission(self, project_permission: ProjectPermission, user):
        project_permission.project = self.config.get("project")
        project_permission.user = user
        project_permission.role = self.config.get("role")
        project_permission.save()

    def create_permission(self, project_permission_dto: ProjectPermissionDTO):
        user, _ = self.get_or_create_user_by_email(project_permission_dto.user)

        project_permission = ProjectPermission.objects.get(
            uuid=self.config.get("uuid"), default=None
        )

        if project_permission is not None:
            self.edit_permission(project_permission, user)

        project_permission = ProjectPermission.objects.create(
            project=project_permission_dto.project,
            user=project_permission_dto.user,
            role=project_permission_dto.role,
        )

    def delete_permission(self, project_permission_dto: ProjectPermissionDTO):
        project_permission = ProjectPermission.objects.get(
            uuid=project_permission_dto.uuid
        )
        project_permission.delete()
