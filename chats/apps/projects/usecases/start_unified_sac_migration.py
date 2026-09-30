import copy
import logging

from django.db import IntegrityError
from django.utils import timezone

from chats.apps.api.v1.internal.eda_clients.change_history_client import (
    publish_change_history,
)
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

    def execute(self, project, user, request=None):
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

        publish_change_history(after=migration, user=user, request=request)

        try:
            self._run(migration, project, user, request)
        except ClearOrgSectorsError as error:
            self._fail(migration, error, user, request)
            raise StartUnifiedSacMigrationError(str(error)) from error
        except Exception as error:
            self._fail(migration, error, user, request)
            raise
        return migration

    def _run(self, migration, project, user, request):
        self._set_status(
            migration, UnifiedSacMigrationStatus.SETTING_PRINCIPAL, user, request
        )
        self._set_principal(project)
        self._set_status(
            migration, UnifiedSacMigrationStatus.PRINCIPAL_SET, user, request
        )

        self._set_status(
            migration, UnifiedSacMigrationStatus.CLOSING_ROOMS, user, request
        )
        CloseOrgRoomsUseCase().execute(project, closed_by=user)
        self._set_status(
            migration, UnifiedSacMigrationStatus.ROOMS_CLOSED, user, request
        )

        self._set_status(
            migration, UnifiedSacMigrationStatus.DELETING_QUEUES, user, request
        )
        ClearOrgSectorsUseCase().execute(
            project, user_email=getattr(user, "email", "") or ""
        )
        self._set_status(
            migration, UnifiedSacMigrationStatus.SECTORS_DELETED, user, request
        )

        self._set_status(
            migration,
            UnifiedSacMigrationStatus.FINISHED,
            user,
            request,
            finished_at=timezone.now(),
        )
        logger.info("Unified SAC migration %s finished", migration.uuid)

    def _set_principal(self, project):
        config = project.config or {}
        config["its_principal"] = True
        project.config = config
        project.save(update_fields=["config", "modified_on"])

        Project.objects.filter(org=project.org).exclude(pk=project.pk).update(
            config={"its_principal": False}
        )

    def _set_status(self, migration, status, user, request, **extra):
        previous = copy.copy(migration)
        migration.status = status
        update_fields = ["status", "modified_on"]
        for field, value in extra.items():
            setattr(migration, field, value)
            update_fields.append(field)
        migration.save(update_fields=update_fields)
        publish_change_history(
            before=previous, after=migration, user=user, request=request
        )
        logger.info("Unified SAC migration %s status %s", migration.uuid, status)

    def _fail(self, migration, error, user, request):
        self._set_status(
            migration,
            UnifiedSacMigrationStatus.FAILED,
            user,
            request,
            error={"detail": str(error)},
            finished_at=timezone.now(),
        )
        logger.info("Unified SAC migration %s failed", migration.uuid)
