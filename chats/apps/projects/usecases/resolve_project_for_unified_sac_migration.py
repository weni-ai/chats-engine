from django.core.exceptions import ValidationError

from chats.apps.projects.models import Project


class MissingProjectUUIDError(Exception):
    pass


class ProjectMismatchError(Exception):
    pass


class ProjectNotFoundError(Exception):
    pass


class ResolveProjectForUnifiedSacMigrationUseCase:
    """Resolve the project a Unified SAC migration should run against."""

    def execute(self, project_uuid, *, jwt_project=None):
        if not project_uuid:
            raise MissingProjectUUIDError()

        if jwt_project is not None:
            if str(jwt_project.uuid) != str(project_uuid):
                raise ProjectMismatchError()
            return jwt_project

        try:
            project = Project.objects.filter(uuid=project_uuid).first()
        except ValidationError:
            project = None
        if project is None:
            raise ProjectNotFoundError()
        return project
