from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status

from chats.apps.api.v1.internal.projects.serializers import (
    CheckAccessReadSerializer,
    ProjectInternalSerializer,
    ProjectPermissionReadSerializer,
    ProjectPermissionSerializer,
)
from chats.apps.projects.models import Project, ProjectPermission

User = get_user_model()


class TestProjectInternalSerializer(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.project_data = {
            "name": "Test Project",
            "date_format": "D",
            "timezone": "America/Sao_Paulo",
            "is_template": True,
            "user_email": "test@example.com",
        }

    def test_serializer_fields(self):
        serializer = ProjectInternalSerializer()
        expected_fields = {
            "uuid",
            "name",
            "date_format",
            "timezone",
            "is_template",
            "user_email",
            "ticketer",
            "queue",
        }
        self.assertEqual(set(serializer.fields.keys()), expected_fields)

    def test_create_project_without_template(self):
        project_data = self.project_data.copy()
        project_data.pop("is_template")
        project_data.pop("user_email")

        serializer = ProjectInternalSerializer(data=project_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        project = serializer.save()

        self.assertEqual(project.name, project_data["name"])
        self.assertEqual(project.date_format, project_data["date_format"])
        self.assertEqual(str(project.timezone), project_data["timezone"])

    @patch(
        "chats.apps.api.v1.internal.projects.serializers.settings.USE_WENI_FLOWS", True
    )
    @patch("chats.apps.api.v1.internal.projects.serializers.FlowRESTClient")
    def test_create_project_with_template(self, mock_flows_client):
        mock_client = MagicMock()
        mock_flows_client.return_value = mock_client

        # Mock successful responses
        mock_sector_response = MagicMock()
        mock_sector_response.status_code = status.HTTP_201_CREATED
        mock_sector_response.json.return_value = {"uuid": "test-uuid"}

        mock_queue_response = MagicMock()
        mock_queue_response.status_code = status.HTTP_201_CREATED

        mock_client.create_ticketer.return_value = mock_sector_response
        mock_client.create_queue.return_value = mock_queue_response

        serializer = ProjectInternalSerializer(data=self.project_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        project = serializer.save()

        self.assertEqual(project.name, self.project_data["name"])
        self.assertTrue(project.permissions.filter(user=self.user).exists())
        self.assertTrue(project.sectors.filter(name="Default Sector").exists())
        self.assertTrue(project.sectors.first().queues.filter(name="Queue 1").exists())

    @patch(
        "chats.apps.api.v1.internal.projects.serializers.settings.USE_WENI_FLOWS", True
    )
    @patch("chats.apps.api.v1.internal.projects.serializers.FlowRESTClient")
    def test_create_project_template_flow_error(self, mock_flows_client):
        mock_client = MagicMock()
        mock_flows_client.return_value = mock_client

        # Mock error response
        mock_sector_response = MagicMock()
        mock_sector_response.status_code = status.HTTP_400_BAD_REQUEST
        mock_sector_response.content = b"Error creating sector"

        mock_client.create_ticketer.return_value = mock_sector_response

        serializer = ProjectInternalSerializer(data=self.project_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with self.assertRaises(Exception) as context:
            serializer.save()

        self.assertIn("Error creating sector", str(context.exception))


class TestProjectPermissionSerializer(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.project = Project.objects.create(
            name="Test Project", date_format="D", timezone="America/Sao_Paulo"
        )

    def test_serializer_fields(self):
        serializer = ProjectPermissionSerializer()
        expected_fields = {
            "uuid",
            "created_on",
            "modified_on",
            "role",
            "project",
            "user",
        }
        self.assertEqual(set(serializer.fields.keys()), expected_fields)

    def test_create_permission(self):
        data = {"role": 1, "project": self.project.uuid, "user": self.user.email}

        serializer = ProjectPermissionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        permission = serializer.save()

        self.assertEqual(permission.role, data["role"])
        self.assertEqual(permission.project, self.project)
        self.assertEqual(permission.user, self.user)


class TestProjectPermissionReadSerializer(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.project = Project.objects.create(
            name="Test Project", date_format="D", timezone="America/Sao_Paulo"
        )
        self.permission = ProjectPermission.objects.create(
            project=self.project, user=self.user, role=1
        )

    def test_serializer_fields(self):
        serializer = ProjectPermissionReadSerializer()
        expected_fields = {
            "uuid",
            "created_on",
            "modified_on",
            "role",
            "project",
            "user",
        }
        self.assertEqual(set(serializer.fields.keys()), expected_fields)

    def test_serialize_permission(self):
        serializer = ProjectPermissionReadSerializer(self.permission)
        data = serializer.data

        self.assertIn("user", data)
        self.assertEqual(data["role"], self.permission.role)
        self.assertEqual(str(data["project"]), str(self.permission.project.uuid))


class TestCheckAccessReadSerializer(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.project = Project.objects.create(
            name="Test Project", date_format="D", timezone="America/Sao_Paulo"
        )
        self.permission = ProjectPermission.objects.create(
            project=self.project, user=self.user, role=1
        )

    def test_serializer_fields(self):
        serializer = CheckAccessReadSerializer()
        self.assertEqual(set(serializer.fields.keys()), {"first_access"})

    def test_serialize_permission(self):
        serializer = CheckAccessReadSerializer(self.permission)
        data = serializer.data
        self.assertIn("first_access", data)
