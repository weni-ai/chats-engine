import uuid

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.dashboard.models import ReportStatus
from chats.apps.projects.models import Project


class ReportStatusViewTests(APITestCase):
    url = "/v1/chats/report/"

    def setUp(self):
        cache.clear()
        self.user = User.objects.create(email="view-user@test.com")
        self.project = Project.objects.create(name="View Project")

    def test_unauthenticated_returns_401(self):
        response = self.client.get(
            self.url,
            {"project_uuid": str(self.project.uuid)},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_project_uuid_returns_400(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_project_uuid_returns_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            self.url,
            {"project_uuid": str(uuid.uuid4())},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_active_report_returns_ready(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            self.url,
            {"project_uuid": str(self.project.uuid)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ready")
        self.assertIsNone(response.data["email"])
        self.assertIsNone(response.data["report_uuid"])

    def test_pending_report_returns_correct_data(self):
        self.client.force_authenticate(user=self.user)
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        response = self.client.get(
            self.url,
            {"project_uuid": str(self.project.uuid)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["report_uuid"], str(report.uuid))

    def test_in_progress_report_returns_correct_data(self):
        self.client.force_authenticate(user=self.user)
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="in_progress",
            fields_config={},
        )

        response = self.client.get(
            self.url,
            {"project_uuid": str(self.project.uuid)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "in_progress")
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["report_uuid"], str(report.uuid))

    def test_cached_response_used_on_second_call(self):
        self.client.force_authenticate(user=self.user)
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        first_response = self.client.get(
            self.url,
            {"project_uuid": str(self.project.uuid)},
        )
        second_response = self.client.get(
            self.url,
            {"project_uuid": str(self.project.uuid)},
        )

        self.assertEqual(first_response.data, second_response.data)

    def test_completed_report_not_returned(self):
        self.client.force_authenticate(user=self.user)
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="ready",
            fields_config={},
        )

        response = self.client.get(
            self.url,
            {"project_uuid": str(self.project.uuid)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ready")
        self.assertIsNone(response.data["email"])
        self.assertIsNone(response.data["report_uuid"])
