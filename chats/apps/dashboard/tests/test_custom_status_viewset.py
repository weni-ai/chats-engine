from datetime import timedelta

import pytz
from django.test import TestCase
from django.utils import timezone
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.projects.viewsets import CustomStatusViewSet
from chats.apps.projects.models import (
    CustomStatus,
    CustomStatusType,
    Project,
    ProjectPermission,
)


class TestCustomStatusViewSet(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.user = User.objects.create(
            email="test@test.com", first_name="Test", last_name="User", is_active=True
        )

        self.project = Project.objects.create(
            name="Test Project", timezone=pytz.timezone("America/Sao_Paulo")
        )

        self.project_permission = ProjectPermission.objects.create(
            user=self.user, project=self.project, status="ONLINE"
        )

        self.status_type = CustomStatusType.objects.create(
            name="Lunch", project=self.project
        )

        self.custom_status = CustomStatus.objects.create(
            user=self.user, status_type=self.status_type, is_active=True, break_time=0
        )

        self.viewset = CustomStatusViewSet()

    def test_last_status_with_active_status(self):
        """Tests the return of user's last active status"""
        request = self.factory.get(
            "/custom-status/last-status/", data={"project_uuid": self.project.uuid}
        )
        force_authenticate(request, user=self.user)
        request = Request(request)
        request.user = self.user

        response = self.viewset.last_status(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["uuid"], str(self.custom_status.uuid))
        self.assertTrue(response.data["is_active"])

    def test_last_status_without_active_status(self):
        """Tests the return when there is no active status"""
        CustomStatus.objects.all().update(is_active=False)

        request = self.factory.get(
            "/custom-status/last-status/", data={"project_uuid": self.project.uuid}
        )
        force_authenticate(request, user=self.user)
        request = Request(request)
        request.user = self.user

        response = self.viewset.last_status(request)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "No status found")

    def test_close_status(self):
        """Tests closing a status"""
        created_on = timezone.now() - timedelta(hours=1)
        self.custom_status.created_on = created_on
        self.custom_status.save()

        request = self.factory.post(
            f"/custom-status/{self.custom_status.pk}/close-status/",
            {},
            format="json",
        )
        force_authenticate(request, user=self.user)
        request = Request(request, parsers=[JSONParser()])
        request.user = self.user

        response = self.viewset.close_status(request, pk=self.custom_status.pk)

        self.assertEqual(response.status_code, 200)
        status_instance = CustomStatus.objects.get(pk=self.custom_status.pk)
        self.assertTrue(status_instance.break_time > 0)

    def test_close_status_not_last_active(self):
        """Tests attempt to close a status that is not the last active one"""
        CustomStatus.objects.create(
            user=self.user, status_type=self.status_type, is_active=True, break_time=0
        )

        end_time = timezone.now() + timedelta(hours=1)
        request = self.factory.post(
            f"/custom-status/{self.custom_status.pk}/close-status/",
            {"end_time": end_time.isoformat()},
            format="json",
        )
        force_authenticate(request, user=self.user)
        request = Request(request, parsers=[JSONParser()])
        request.user = self.user

        response = self.viewset.close_status(request, pk=self.custom_status.pk)

        self.assertEqual(response.status_code, 400)
        self.assertIn("not the last active status", response.data["detail"])

    def test_close_status_missing_end_time(self):
        """Tests attempt to close a status without providing end_time"""
        request = self.factory.post(
            f"/custom-status/{self.custom_status.pk}/close-status/", {}, format="json"
        )
        force_authenticate(request, user=self.user)
        request = Request(request, parsers=[JSONParser()])
        request.user = self.user

        response = self.viewset.close_status(request, pk=self.custom_status.pk)

        self.assertEqual(response.status_code, 200)
        self.custom_status.refresh_from_db()
        self.assertFalse(self.custom_status.is_active)

    def test_close_status_invalid_end_time(self):
        """Tests attempt to close a status with invalid end_time format"""
        request = self.factory.post(
            f"/custom-status/{self.custom_status.pk}/close-status/",
            {"end_time": "invalid-date-format"},
            format="json",
        )
        force_authenticate(request, user=self.user)
        request = Request(request, parsers=[JSONParser()])
        request.user = self.user

        response = self.viewset.close_status(request, pk=self.custom_status.pk)

        self.assertEqual(response.status_code, 200)
        self.custom_status.refresh_from_db()
        self.assertFalse(self.custom_status.is_active)
