from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.api.utils import create_user_and_token
from chats.apps.projects.models import Project


def grant_internal_communication(user):
    content_type = ContentType.objects.get_for_model(User)
    permission, _ = Permission.objects.get_or_create(
        codename="can_communicate_internally",
        content_type=content_type,
        defaults={"name": "can communicate internally"},
    )
    user.user_permissions.add(permission)
    user = User.objects.get(pk=user.pk)
    return user


class UnifiedSacInternalAuthTests(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("sacinternal")
        self.user = grant_internal_communication(self.user)
        self.project = Project.objects.create(name="Principal", org="org-internal-auth")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.status_url = reverse(
            "project-unified-sac-migration-status",
            kwargs={"uuid": str(self.project.uuid)},
        )
        self.start_url = reverse(
            "project-start-unified-sac-migration",
            kwargs={"uuid": str(self.project.uuid)},
        )
        self.principal_url = reverse(
            "project-set-project-as-principal",
            kwargs={"uuid": str(self.project.uuid)},
        )

    def test_internal_user_reads_status_without_project_permission(self):
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["detail"],
            "No Unified SAC migration for this organization.",
        )

    @patch("chats.apps.api.v1.projects.viewsets.StartUnifiedSacMigrationUseCase")
    def test_internal_user_starts_migration_without_project_permission(
        self, mock_usecase
    ):
        mock_usecase.return_value.execute.return_value = SimpleNamespace(
            uuid=uuid4(),
            status="FINISHED",
        )
        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "FINISHED")

    def test_internal_user_sets_principal_without_project_permission(self):
        response = self.client.post(self.principal_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertTrue(self.project.config.get("its_principal"))
