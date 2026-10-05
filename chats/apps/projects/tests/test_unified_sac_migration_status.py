from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.projects.models import (
    Project,
    ProjectPermission,
    UnifiedSacMigration,
    UnifiedSacMigrationStatus,
)


class UnifiedSacMigrationStatusEndpointTests(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("migrationstatus")
        self.project = Project.objects.create(name="Principal", org="org-status")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.url = reverse(
            "project-unified-sac-migration-status",
            kwargs={"uuid": str(self.project.uuid)},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_get_returns_404_when_org_has_no_migration(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_returns_latest_migration_status(self):
        older = UnifiedSacMigration.objects.create(
            org="org-status",
            principal_project=self.project,
            created_by=self.user,
            status=UnifiedSacMigrationStatus.FAILED,
            started_at=timezone.now(),
            finished_at=timezone.now(),
            error={"detail": "old"},
        )
        latest = UnifiedSacMigration.objects.create(
            org="org-status",
            principal_project=self.project,
            created_by=self.user,
            status=UnifiedSacMigrationStatus.CLOSING_ROOMS,
            started_at=timezone.now(),
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(latest.uuid))
        self.assertEqual(
            response.data["status"], UnifiedSacMigrationStatus.CLOSING_ROOMS
        )
        self.assertNotEqual(response.data["uuid"], str(older.uuid))
