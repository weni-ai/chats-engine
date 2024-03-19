from dataclasses import dataclass

from django.contrib.auth import get_user_model

from ..models import ProjectPermission
from .exceptions import InvalidProjectData

User = get_user_model()


@dataclass
class ProjectPermissionCreationDTO:
    uuid: str
    project: str
    user: str
    role: str


class ProjectPermissionCreationUseCase:
    def create_permission(self, project_permission_dto: ProjectPermissionCreationDTO):

        # verificar se ja existe

        project_permission = ProjectPermission.objects.create(
            uuid=project_permission_dto.uuid,
            project=project_permission_dto.project,
            user=project_permission_dto.user,
            role=project_permission_dto.role,
        )
