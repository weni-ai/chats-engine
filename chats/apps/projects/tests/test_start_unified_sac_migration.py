from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.projects.models import (
    Project,
    ProjectPermission,
    UnifiedSacMigration,
    UnifiedSacMigrationStatus,
)
from chats.apps.projects.usecases.clear_org_sectors import ClearOrgSectorsError
from chats.apps.projects.usecases.start_unified_sac_migration import (
    StartUnifiedSacMigrationUseCase,
)


class StartUnifiedSacMigrationUseCaseTests(APITestCase):
    def setUp(self):
        self.user, _ = create_user_and_token("migrationuser")
        self.org_id = "org-migration-001"
        self.project = Project.objects.create(name="Principal", org=self.org_id)
        self.other = Project.objects.create(name="Secondary", org=self.org_id)

    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.ClearOrgSectorsUseCase.execute"
    )
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.CloseOrgRoomsUseCase.execute"
    )
    def test_execute_records_finished_migration(self, close_rooms, clear_sectors):
        migration = StartUnifiedSacMigrationUseCase().execute(
            self.project, user=self.user
        )

        self.project.refresh_from_db()
        self.other.refresh_from_db()
        self.assertTrue(self.project.config.get("its_principal"))
        self.assertFalse(self.other.config.get("its_principal"))
        self.assertEqual(migration.status, UnifiedSacMigrationStatus.FINISHED)
        self.assertEqual(migration.org, self.org_id)
        self.assertEqual(migration.principal_project, self.project)
        self.assertEqual(migration.created_by, self.user)
        close_rooms.assert_called_once_with(self.project, closed_by=self.user)
        clear_sectors.assert_called_once()

    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.ClearOrgSectorsUseCase.execute",
        side_effect=ClearOrgSectorsError("flows failed"),
    )
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.CloseOrgRoomsUseCase.execute"
    )
    def test_execute_marks_failed_when_sectors_cannot_be_deleted(
        self, close_rooms, clear_sectors
    ):
        with self.assertRaises(Exception):
            StartUnifiedSacMigrationUseCase().execute(self.project, user=self.user)

        migration = UnifiedSacMigration.objects.get(org=self.org_id)
        self.assertEqual(migration.status, UnifiedSacMigrationStatus.FAILED)
        self.assertEqual(migration.error, {"detail": "flows failed"})

    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.publish_change_history"
    )
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.ClearOrgSectorsUseCase.execute"
    )
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.CloseOrgRoomsUseCase.execute"
    )
    def test_execute_publishes_create_and_status_changes(
        self, close_rooms, clear_sectors, publish
    ):
        migration = StartUnifiedSacMigrationUseCase().execute(
            self.project, user=self.user
        )
        actions = [call.kwargs for call in publish.call_args_list]
        self.assertIsNone(actions[0]["before"])
        self.assertEqual(actions[0]["after"].status, UnifiedSacMigrationStatus.PENDING)
        self.assertEqual(
            actions[-1]["after"].status, UnifiedSacMigrationStatus.FINISHED
        )
        self.assertEqual(
            actions[-1]["before"].status, UnifiedSacMigrationStatus.SECTORS_DELETED
        )
        self.assertEqual(publish.call_count, 8)
        self.assertEqual(migration.status, UnifiedSacMigrationStatus.FINISHED)

    def test_execute_rejects_project_without_org(self):
        project = Project.objects.create(name="No org")
        with self.assertRaises(Exception):
            StartUnifiedSacMigrationUseCase().execute(project, user=self.user)
        self.assertFalse(UnifiedSacMigration.objects.exists())


class StartUnifiedSacMigrationEndpointTests(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("migrationendpoint")
        self.project = Project.objects.create(name="Principal", org="org-endpoint")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.url = reverse(
            "project-start-unified-sac-migration",
            kwargs={"uuid": str(self.project.uuid)},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.ClearOrgSectorsUseCase.execute"
    )
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.CloseOrgRoomsUseCase.execute"
    )
    def test_post_returns_finished_migration(self, close_rooms, clear_sectors):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        migration = UnifiedSacMigration.objects.get(org="org-endpoint")
        self.assertEqual(response.data["uuid"], str(migration.uuid))
        self.assertEqual(response.data["status"], UnifiedSacMigrationStatus.FINISHED)

    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.ClearOrgSectorsUseCase.execute"
    )
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.CloseOrgRoomsUseCase.execute"
    )
    def test_post_returns_409_when_migration_is_in_progress(
        self, close_rooms, clear_sectors
    ):
        self.client.post(self.url)
        UnifiedSacMigration.objects.filter(org="org-endpoint").update(
            status=UnifiedSacMigrationStatus.CLOSING_ROOMS,
            finished_at=None,
        )
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
