import uuid
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.projects.models.models import Project

USECASE_PATH = (
    "chats.apps.api.v2.internal.dashboard.usecases.agents"
    ".InternalDashboardAgentsUsecase.execute"
)


class BaseInternalDashboardViewsetV2Tests(APITestCase):
    def get_agent_metrics(self, project_uuid: str, filters: dict = {}):
        url = f"/v2/internal/dashboard/{project_uuid}/agent/"
        return self.client.get(url, filters)


class TestInternalDashboardViewsetV2AsAnonymousUser(
    BaseInternalDashboardViewsetV2Tests,
):
    def test_agent_metrics_returns_401(self):
        response = self.get_agent_metrics(uuid.uuid4())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestInternalDashboardViewsetV2AsAuthenticatedUser(
    BaseInternalDashboardViewsetV2Tests,
):
    def setUp(self):
        self.user = User.objects.create(email="testuser@test.com")
        self.project = Project.objects.create(name="Test Project")
        self.client.force_authenticate(user=self.user)
        self.valid_filters = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "agent": "agent@test.com",
            "sector": ["sector-uuid"],
            "tag": ["tag1"],
            "queue": ["queue-uuid"],
            "user_request": "user@test.com",
            "is_weni_admin": True,
            "ordering": "status",
            "status": ["online"],
            "custom_status": ["Pausa"],
        }

    def test_agent_metrics_returns_403_without_internal_permission(self):
        response = self.get_agent_metrics(self.project.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    @patch(USECASE_PATH)
    def test_agent_metrics_returns_404_for_nonexistent_project(self, mock_execute):
        response = self.get_agent_metrics(uuid.uuid4(), self.valid_filters)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_execute.assert_not_called()

    @with_internal_auth
    @patch(USECASE_PATH)
    def test_agent_metrics_returns_200(self, mock_execute):
        mock_execute.return_value = []

        response = self.get_agent_metrics(self.project.uuid, self.valid_filters)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    @with_internal_auth
    @patch(USECASE_PATH)
    def test_agent_metrics_calls_usecase_with_project_and_filters(self, mock_execute):
        mock_execute.return_value = []

        self.get_agent_metrics(self.project.uuid, self.valid_filters)

        mock_execute.assert_called_once()
        project_arg, filters_arg = mock_execute.call_args[0]
        self.assertEqual(project_arg, self.project)
        self.assertIsInstance(filters_arg, dict)
        self.assertEqual(str(filters_arg["start_date"]), "2024-01-01")
        self.assertEqual(str(filters_arg["end_date"]), "2024-01-31")
        self.assertEqual(filters_arg["agent"], "agent@test.com")

    @with_internal_auth
    @patch(USECASE_PATH)
    def test_agent_metrics_returns_serialized_agents(self, mock_execute):
        mock_execute.return_value = [
            {
                "first_name": "Agent",
                "last_name": "One",
                "email": "agent1@test.com",
                "status": "ONLINE",
                "status_order": 1,
                "has_active_custom_status": False,
                "is_deleted": False,
                "closed": 5,
                "opened": 2,
                "avg_first_response_time": 30,
                "avg_message_response_time": 15,
                "avg_interaction_time": 120,
                "custom_status": None,
            },
        ]

        response = self.get_agent_metrics(self.project.uuid, self.valid_filters)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["agent"]["email"], "agent1@test.com")
        self.assertEqual(results[0]["agent"]["name"], "Agent One")
        self.assertFalse(results[0]["agent"]["is_deleted"])
        self.assertEqual(results[0]["closed"], 5)
        self.assertEqual(results[0]["opened"], 2)
