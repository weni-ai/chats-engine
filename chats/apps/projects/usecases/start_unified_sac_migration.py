import logging

from django.db import IntegrityError
from django.utils import timezone

from chats.apps.projects.models import (
    Project,
    UnifiedSacMigration,
    UnifiedSacMigrationStatus,
)
from chats.apps.projects.usecases.clear_org_sectors import (
    ClearOrgSectorsError,
    ClearOrgSectorsUseCase,
)
from chats.apps.projects.usecases.close_org_rooms import CloseOrgRoomsUseCase

logger = logging.getLogger(__name__)


class StartUnifiedSacMigrationError(Exception):
    pass


class UnifiedSacMigrationInProgressError(StartUnifiedSacMigrationError):
    pass


class StartUnifiedSacMigrationUseCase:
    """Start a Unified SAC migration and record each step on UnifiedSacMigration."""

    def execute(self, project, user):
        if not project.org:
            raise StartUnifiedSacMigrationError("Project has no organization uuid.")

        try:
            migration = UnifiedSacMigration.objects.create(
                org=project.org,
                principal_project=project,
                created_by=user,
                status=UnifiedSacMigrationStatus.PENDING,
                started_at=timezone.now(),
            )
        except IntegrityError as error:
            raise UnifiedSacMigrationInProgressError(
                "This organization already has a migration in progress."
            ) from error

        try:
            self._run(migration, project, user)
        except ClearOrgSectorsError as error:
            self._fail(migration, error)
            raise StartUnifiedSacMigrationError(str(error)) from error
        except Exception as error:
            self._fail(migration, error)
            raise
        return migration

    def _run(self, migration, project, user):
        self._set_status(migration, UnifiedSacMigrationStatus.SETTING_PRINCIPAL)
        self._set_principal(project)
        self._set_status(migration, UnifiedSacMigrationStatus.PRINCIPAL_SET)

        self._set_status(migration, UnifiedSacMigrationStatus.CLOSING_ROOMS)
        CloseOrgRoomsUseCase().execute(project, closed_by=user)
        self._set_status(migration, UnifiedSacMigrationStatus.ROOMS_CLOSED)

        self._set_status(migration, UnifiedSacMigrationStatus.DELETING_QUEUES)
        ClearOrgSectorsUseCase().execute(
            project, user_email=getattr(user, "email", "") or ""
        )
        self._set_status(migration, UnifiedSacMigrationStatus.SECTORS_DELETED)

        migration.status = UnifiedSacMigrationStatus.FINISHED
        migration.finished_at = timezone.now()
        migration.save(update_fields=["status", "finished_at", "modified_on"])
        logger.info("Unified SAC migration %s finished", migration.uuid)

    def _set_principal(self, project):
        config = project.config or {}
        config["its_principal"] = True
        project.config = config
        project.save(update_fields=["config", "modified_on"])

        Project.objects.filter(org=project.org).exclude(pk=project.pk).update(
            config={"its_principal": False}
        )

    def _set_status(self, migration, status):
        migration.status = status
        migration.save(update_fields=["status", "modified_on"])
        logger.info("Unified SAC migration %s status %s", migration.uuid, status)

    def _fail(self, migration, error):
        migration.status = UnifiedSacMigrationStatus.FAILED
        migration.error = {"detail": str(error)}
        migration.finished_at = timezone.now()
        migration.save(update_fields=["status", "error", "finished_at", "modified_on"])
        logger.info("Unified SAC migration %s failed", migration.uuid)
