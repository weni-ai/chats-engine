from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from chats.apps.projects.models import CustomStatusType, CustomStatus
import uuid


class PermissionTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.project_2 = Project.objects.get(pk="32e74fec-0dd7-413d-8062-9659f2e213d2")
        self.manager_user = User.objects.get(pk=9)
        self.login_token = Token.objects.get_or_create(user=self.manager_user)[0]

    def test_get_first_access_status(self):
        """
        Verify if the Project Permission its returning the correct value from first_access field.
        """
        url = reverse("project_permission-list")
        url_action = f"{url}verify_access/"
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url_action, data={"project": self.project.pk})
        self.assertEqual(response.data.get("first_access"), True)

    def test_get_first_access_status_without_permission(self):
        """
        Ensure that users who dont have permission in a determined project,
        cannot get the value off first_access field.
        """
        url = reverse("project_permission-list")
        url_action = f"{url}verify_access/"
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url_action, data={"project": self.project_2.pk})
        self.assertEqual(response.data.get("first_access"), None)
        self.assertEqual(
            response.data["Detail"], "You dont have permission in this project."
        )

    def test_update_first_access_status(self):
        """
        Verify if the endpoint its updating the first access correctly.
        """
        url = reverse("project_permission-list")
        url_action = f"{url}update_access/?project=34a93b52-231e-11ed-861d-0242ac120002"
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.patch(url_action)
        self.assertEqual(response.data.get("first_access"), False)

    def test_patch_first_access_status_without_permission(self):
        """
        Ensure that users who dont have permission in a determined project, cannot change the first_access field.
        """
        url = reverse("project_permission-list")
        url_action = f"{url}update_access/?project=32e74fec-0dd7-413d-8062-9659f2e213d2"
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.patch(url_action)
        self.assertEqual(response.data.get("first_access"), None)
        self.assertEqual(
            response.data["Detail"], "You dont have permission in this project."
        )


class TestCustomStatusViewSet(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self):
        self.user = User.objects.get(pk=9)
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.status_type = CustomStatusType.objects.create(
            name="Test Status Type",
            project=self.project,
        )

    def test_create_custom_status(self):
        body = {
            "user": self.user.email,
            "status_type": self.status_type.pk,
            "is_active": True,
        }

        response = self.client.post(reverse("customstatus-list"), body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            CustomStatus.objects.filter(
                user=self.user, status_type=self.status_type
            ).exists()
        )

    def test_last_status(self):
        CustomStatus.objects.create(
            user=self.user,
            status_type=self.status_type,
            is_active=True,
            break_time=0,
        )
        CustomStatus.objects.create(
            user=self.user,
            status_type=self.status_type,
            is_active=True,
            break_time=1,
        )

        response = self.client.get(reverse("customstatus-last-status"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["break_time"], 1)
