from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.projects.models.models import Project, ProjectPermission, User


class BaseTestProjectViewSet(APITestCase):
    def retrieve(self, project_uuid: str) -> Response:
        url = reverse("project_internal-detail", kwargs={"uuid": project_uuid})
        return self.client.get(url)

    def list(self) -> Response:
        url = reverse("project_internal-list")
        return self.client.get(url)

    def create(self, data: dict) -> Response:
        url = reverse("project_internal-list")
        return self.client.post(url, data, format="json")

    def update(self, project_uuid: str, data: dict) -> Response:
        url = reverse("project_internal-detail", kwargs={"uuid": project_uuid})
        return self.client.put(url, data, format="json")

    def partial_update(self, project_uuid: str, data: dict) -> Response:
        url = reverse("project_internal-detail", kwargs={"uuid": project_uuid})
        return self.client.patch(url, data, format="json")

    def destroy(self, project_uuid: str) -> Response:
        url = reverse("project_internal-detail", kwargs={"uuid": project_uuid})
        return self.client.delete(url)


class TestProjectViewSetAsAnonymousUser(BaseTestProjectViewSet):
    def test_retrieve_project_as_anonymous_user(self):
        response = self.retrieve("123")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_projects_as_anonymous_user(self):
        response = self.list()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_project_as_anonymous_user(self):
        response = self.create({"name": "test"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_project_as_anonymous_user(self):
        response = self.update("123", {"name": "test"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_partial_update_project_as_anonymous_user(self):
        response = self.partial_update("123", {"name": "test"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_destroy_project_as_anonymous_user(self):
        response = self.destroy("123")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestProjectViewSetAsAuthenticatedUser(BaseTestProjectViewSet):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.user = User.objects.create(email="testuser@test.com")

        self.client.force_authenticate(self.user)

    def tearDown(self):
        cache.clear()

    def test_cannot_retrieve_project_without_internal_communication_permission(self):
        response = self.retrieve(self.project.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_retrieve_project(self):
        response = self.retrieve(self.project.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cannot_list_projects_without_internal_communication_permission(self):
        response = self.list()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_list_projects(self):
        response = self.list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_cannot_create_project_without_internal_communication_permission(self):
        response = self.create({"name": "New Project"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_create_project(self):
        response = self.create({"name": "New Project", "timezone": "UTC"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 2)

    def test_cannot_update_project_without_internal_communication_permission(self):
        response = self.update(self.project.uuid, {"name": "Updated Name"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_update_project(self):
        response = self.update(
            self.project.uuid, {"name": "Updated Name", "timezone": "UTC"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Updated Name")

    def test_cannot_partial_update_project_without_internal_communication_permission(
        self,
    ):
        response = self.partial_update(self.project.uuid, {"name": "Updated Name"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_partial_update_project(self):
        response = self.partial_update(self.project.uuid, {"name": "Updated Name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Updated Name")

    def test_cannot_destroy_project_without_internal_communication_permission(self):
        response = self.destroy(self.project.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_destroy_project(self):
        response = self.destroy(self.project.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Project.objects.count(), 0)


class BaseTestProjectPermissionViewSet(APITestCase):
    def list(self, project_uuid: str = None) -> Response:
        url = reverse("project_permission_internal-list")
        params = {}
        if project_uuid:
            params["project"] = project_uuid
        return self.client.get(url, params)

    def create(self, data: dict) -> Response:
        url = reverse("project_permission_internal-list")
        return self.client.post(url, data, format="json")

    def retrieve(self, permission_uuid: str) -> Response:
        url = reverse(
            "project_permission_internal-detail", kwargs={"uuid": permission_uuid}
        )
        return self.client.get(url)

    def update(self, permission_uuid: str, data: dict) -> Response:
        url = reverse(
            "project_permission_internal-detail", kwargs={"uuid": permission_uuid}
        )
        return self.client.put(url, data, format="json")

    def partial_update(self, permission_uuid: str, data: dict) -> Response:
        url = reverse(
            "project_permission_internal-detail", kwargs={"uuid": permission_uuid}
        )
        return self.client.patch(url, data, format="json")

    def destroy(self, permission_uuid: str) -> Response:
        url = reverse(
            "project_permission_internal-detail", kwargs={"uuid": permission_uuid}
        )
        return self.client.delete(url)

    def status(self, data: dict, method: str = "post") -> Response:
        url = reverse("project_permission_internal-status")
        if method.lower() == "post":
            return self.client.post(url, data, format="json")
        return self.client.get(url, data)


class TestProjectPermissionViewSetAsAnonymousUser(BaseTestProjectPermissionViewSet):
    def test_list_permissions_as_anonymous_user(self):
        response = self.list()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_permission_as_anonymous_user(self):
        response = self.create({})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_permission_as_anonymous_user(self):
        response = self.retrieve("123")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_permission_as_anonymous_user(self):
        response = self.update("123", {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_partial_update_permission_as_anonymous_user(self):
        response = self.partial_update("123", {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_destroy_permission_as_anonymous_user(self):
        response = self.destroy("123")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_status_as_anonymous_user(self):
        response = self.status({}, method="post")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.status({}, method="get")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestProjectPermissionViewSetAsAuthenticatedUser(BaseTestProjectPermissionViewSet):
    def setUp(self):
        self.user = User.objects.create(email="testuser@test.com")
        self.project = Project.objects.create(name="Test Project")
        self.permission = ProjectPermission.objects.create(
            project=self.project, user=self.user, role=ProjectPermission.ROLE_ADMIN
        )
        self.client.force_authenticate(self.user)

    def tearDown(self):
        cache.clear()

    def test_cannot_list_permissions_without_internal_auth(self):
        response = self.list()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_list_permissions(self):
        response = self.list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    @with_internal_auth
    def test_list_permissions_with_project_filter(self):
        other_project = Project.objects.create(name="Other Project")
        response = self.list(project_uuid=str(other_project.uuid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)
        response = self.list(project_uuid=str(self.project.uuid))
        self.assertEqual(len(response.data["results"]), 1)

    def test_cannot_create_permission_without_internal_auth(self):
        response = self.create({})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    @override_settings(OIDC_ENABLED=True)
    @patch(
        "chats.apps.api.v1.internal.projects.viewsets.persist_keycloak_user_by_email"
    )
    def test_create_permission(self, mock_persist_keycloak):
        new_user = User.objects.create(email="newuser@test.com")
        data = {
            "project": str(self.project.uuid),
            "user": new_user.email,
            "role": ProjectPermission.ROLE_ADMIN,
        }
        response = self.create(data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_persist_keycloak.assert_called_once_with(new_user.email)
        self.assertTrue(
            ProjectPermission.objects.filter(
                project=self.project, user=new_user
            ).exists()
        )

    def test_cannot_retrieve_permission_without_internal_auth(self):
        response = self.retrieve(self.permission.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_retrieve_permission(self):
        response = self.retrieve(self.permission.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(self.permission.uuid))

    def test_cannot_update_permission_without_internal_auth(self):
        response = self.update(self.permission.uuid, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    @override_settings(OIDC_ENABLED=False)
    @patch(
        "chats.apps.api.v1.internal.projects.viewsets.persist_keycloak_user_by_email"
    )
    def test_update_permission_with_put(self, mock_persist_keycloak):
        data = {
            "project": str(self.project.uuid),
            "user": self.user.email,
            "role": ProjectPermission.ROLE_ATTENDANT,
        }
        response = self.update(str(self.permission.uuid), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cannot_destroy_permission_without_internal_auth(self):
        response = self.destroy(self.permission.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_destroy_permission(self):
        self.assertEqual(ProjectPermission.objects.count(), 1)
        response = self.destroy(self.permission.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ProjectPermission.objects.count(), 0)

    def test_cannot_use_status_action_without_internal_auth(self):
        response = self.status({}, method="post")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.status({}, method="get")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(
        "chats.apps.api.v1.internal.projects.viewsets.start_queue_priority_routing_for_all_queues_in_project"
    )
    def test_status_action_post(self, mock_start_routing):
        data = {"project": str(self.project.uuid), "status": "online"}
        response = self.status(data, method="post")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["connection_status"], "ONLINE")
        self.permission.refresh_from_db()
        self.assertEqual(self.permission.status, ProjectPermission.STATUS_ONLINE)
        mock_start_routing.assert_called_once_with(self.project)

    def test_status_action_get(self):
        self.permission.status = ProjectPermission.STATUS_AWAY
        self.permission.save()
        data = {"project": str(self.project.uuid)}
        response = self.status(data, method="get")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["connection_status"], "AWAY")
