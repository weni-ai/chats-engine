import uuid
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.api.authentication.services.jwt_service import JWTService
from chats.apps.api.authentication.tests.test_jwt_service import (
    generate_private_key,
    generate_private_key_pem,
    generate_public_key,
    generate_public_key_pem,
)
from chats.apps.api.utils import create_user_and_token
from chats.apps.projects.models import (
    Project,
    ProjectPermission,
    UnifiedSacMigration,
    UnifiedSacMigrationStatus,
)
from chats.apps.projects.usecases.clear_org_sectors import ClearOrgSectorsError
from chats.apps.projects.usecases.start_unified_sac_migration import (
    StartUnifiedSacMigrationError,
    StartUnifiedSacMigrationUseCase,
)

TEST_PRIVATE_KEY = generate_private_key()
TEST_PRIVATE_KEY_PEM = generate_private_key_pem(TEST_PRIVATE_KEY)
TEST_PUBLIC_KEY = generate_public_key(TEST_PRIVATE_KEY)
TEST_PUBLIC_KEY_PEM = generate_public_key_pem(TEST_PUBLIC_KEY)


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
        with self.assertRaises(StartUnifiedSacMigrationError):
            StartUnifiedSacMigrationUseCase().execute(self.project, user=self.user)

        migration = UnifiedSacMigration.objects.get(org=self.org_id)
        self.assertEqual(migration.status, UnifiedSacMigrationStatus.FAILED)
        self.assertEqual(migration.error, {"detail": "flows failed"})

    def test_execute_rejects_project_without_org(self):
        project = Project.objects.create(name="No org")
        with self.assertRaises(StartUnifiedSacMigrationError):
            StartUnifiedSacMigrationUseCase().execute(project, user=self.user)
        self.assertFalse(UnifiedSacMigration.objects.exists())


class StartUnifiedSacMigrationEndpointTests(APITestCase):
    def setUp(self):
        self.user, _ = create_user_and_token("migrationendpoint")
        self.project = Project.objects.create(name="Principal", org="org-endpoint")
        self.url = reverse("project-start-unified-sac-migration")
        self.client.force_authenticate(self.user)

    def tearDown(self):
        cache.clear()

    def post(self, data=None):
        if data is None:
            data = {"project_uuid": str(self.project.uuid)}
        return self.client.post(self.url, data, format="json")

    @with_internal_auth
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.ClearOrgSectorsUseCase.execute"
    )
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.CloseOrgRoomsUseCase.execute"
    )
    def test_post_returns_finished_migration(self, close_rooms, clear_sectors):
        self.assertFalse(ProjectPermission.objects.filter(user=self.user).exists())
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        migration = UnifiedSacMigration.objects.get(org="org-endpoint")
        self.assertEqual(response.data["uuid"], str(migration.uuid))
        self.assertEqual(response.data["status"], UnifiedSacMigrationStatus.FINISHED)
        self.assertEqual(migration.created_by, self.user)

    @with_internal_auth
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.ClearOrgSectorsUseCase.execute"
    )
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.CloseOrgRoomsUseCase.execute"
    )
    def test_post_returns_409_when_migration_is_in_progress(
        self, close_rooms, clear_sectors
    ):
        self.post()
        UnifiedSacMigration.objects.filter(org="org-endpoint").update(
            status=UnifiedSacMigrationStatus.CLOSING_ROOMS,
            finished_at=None,
        )
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_post_without_internal_permission_returns_403(self):
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @with_internal_auth
    def test_post_without_project_uuid_returns_400(self):
        response = self.post({})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project_uuid", response.data)

    @with_internal_auth
    def test_post_unknown_project_returns_404(self):
        response = self.post({"project_uuid": str(uuid.uuid4())})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class StartUnifiedSacMigrationJWTEndpointTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Principal", org="org-jwt")
        self.url = reverse("project-start-unified-sac-migration")

    def tearDown(self):
        cache.clear()

    @override_settings(
        JWT_SECRET_KEY=TEST_PRIVATE_KEY_PEM,
        JWT_PUBLIC_KEY=TEST_PUBLIC_KEY_PEM,
    )
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.ClearOrgSectorsUseCase.execute"
    )
    @patch(
        "chats.apps.projects.usecases.start_unified_sac_migration.CloseOrgRoomsUseCase.execute"
    )
    def test_post_with_matching_jwt_returns_finished_migration(
        self, close_rooms, clear_sectors
    ):
        token = JWTService().generate_jwt_token(project_uuid=self.project.uuid)
        response = self.client.post(
            self.url,
            {"project_uuid": str(self.project.uuid)},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        migration = UnifiedSacMigration.objects.get(org="org-jwt")
        self.assertEqual(response.data["uuid"], str(migration.uuid))
        self.assertEqual(response.data["status"], UnifiedSacMigrationStatus.FINISHED)
        self.assertIsNone(migration.created_by)

    @override_settings(
        JWT_SECRET_KEY=TEST_PRIVATE_KEY_PEM,
        JWT_PUBLIC_KEY=TEST_PUBLIC_KEY_PEM,
    )
    def test_post_with_jwt_for_another_project_returns_403(self):
        other = Project.objects.create(name="Other", org="org-jwt-other")
        token = JWTService().generate_jwt_token(project_uuid=self.project.uuid)
        response = self.client.post(
            self.url,
            {"project_uuid": str(other.uuid)},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
