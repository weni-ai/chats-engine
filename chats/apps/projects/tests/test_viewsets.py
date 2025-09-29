import uuid
from unittest.mock import patch

from django.urls import reverse
from django.utils.crypto import get_random_string
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from rest_framework.response import Response
from rest_framework import status

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.projects.tests.decorators import with_project_permission


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


class BaseTestUpdateProjectViewSet(APITestCase):
    def update(self, project_uuid: str, data: dict) -> Response:
        url = reverse("project-detail", kwargs={"uuid": project_uuid})

        return self.client.patch(url, data, format="json")


class BaseTestUpdateProjectViewSetAnonymousUser(BaseTestUpdateProjectViewSet):
    def test_cannot_update_project_when_unauthenticated(self):
        response = self.update(uuid.uuid4(), {"name": "test"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BaseTestUpdateProjectViewSetAuthenticatedUser(BaseTestUpdateProjectViewSet):
    def setUp(self):
        self.user = User.objects.create(email="test@test.com")
        self.project = Project.objects.create(name="test")

        self.client.force_authenticate(self.user)

    def test_cannot_update_project_without_permission(self):
        response = self.update(self.project.uuid, {"name": "test"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @with_project_permission
    def test_update_project(self):
        new_name = get_random_string(length=10)
        response = self.update(self.project.uuid, {"name": new_name})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.project.refresh_from_db(fields=["name"])
        self.assertEqual(self.project.name, new_name)

    @with_project_permission
    @patch("chats.apps.feature_flags.utils.is_feature_active")
    def test_cannot_enable_csat_when_feature_flag_is_off(self, mock_is_feature_active):
        self.project.is_csat_enabled = False
        self.project.save(update_fields=["is_csat_enabled"])

        mock_is_feature_active.return_value = False

        response = self.update(self.project.uuid, {"is_csat_enabled": True})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["is_csat_enabled"][0].code, "csat_feature_flag_is_off"
        )

    @with_project_permission
    @patch("chats.apps.feature_flags.utils.is_feature_active")
    def test_can_enable_csat_when_feature_flag_is_on(self, mock_is_feature_active):
        mock_is_feature_active.return_value = True
        response = self.update(self.project.uuid, {"is_csat_enabled": True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.project.refresh_from_db(update_fields=["is_csat_enabled"])
        self.assertTrue(self.project.is_csat_enabled)
