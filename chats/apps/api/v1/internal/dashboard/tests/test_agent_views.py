from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.api.v1.internal.dashboard.viewsets import _build_status_filter
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


User = get_user_model()


class BuildStatusFilterTests(SimpleTestCase):
    def test_empty_returns_none(self):
        self.assertIsNone(_build_status_filter([]))
        self.assertIsNone(_build_status_filter(None))

    def test_online(self):
        q = _build_status_filter(["online"])
        self.assertIsInstance(q, Q)

    def test_custom_breaks_and_offline(self):
        q = _build_status_filter(["custom_breaks", "offline"])
        self.assertIsInstance(q, Q)

    def test_comma_separated(self):
        q = _build_status_filter(["online,offline"])
        self.assertIsInstance(q, Q)

    def test_unknown_only_returns_none(self):
        self.assertIsNone(_build_status_filter(["unknown"]))


class InternalDashboardAgentViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(email="internal-dash@test.com")
        self.project = Project.objects.create(name="Internal Dash Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Sector",
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue = Queue.objects.create(sector=self.sector, name="Queue")
        ProjectPermission.objects.create(
            user=self.user,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
            status=ProjectPermission.STATUS_ONLINE,
        )
        self.client.force_authenticate(user=self.user)
        self.base = f"/v1/internal/dashboard/{self.project.uuid}"

    @with_internal_auth
    @patch(
        "chats.apps.api.v1.internal.dashboard.viewsets.AgentsService.get_agents_data"
    )
    def test_agent_endpoint(self, mock_get_agents):
        mock_get_agents.return_value = [
            {
                "email": "agent@test.com",
                "first_name": "Agent",
                "last_name": "One",
                "status": "ONLINE",
                "opened": 1,
                "closed": 0,
                "avg_first_response_time": 10,
                "avg_message_response_time": 20,
                "avg_interaction_time": 30,
                "custom_status": [],
            }
        ]
        response = self.client.get(f"{self.base}/agent/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    @with_internal_auth
    @patch(
        "chats.apps.api.v1.internal.dashboard.viewsets.AgentsService.get_agents_data"
    )
    def test_agent_endpoint_with_status_filter(self, mock_get_agents):
        qs = MagicMock()
        qs.filter.return_value = qs
        mock_get_agents.return_value = qs

        # paginate_queryset on MagicMock may return weird results; return a list from filter
        filtered = [
            {
                "email": "online@test.com",
                "first_name": "On",
                "last_name": "Line",
                "status": "ONLINE",
                "opened": 0,
                "closed": 0,
                "custom_status": [],
            }
        ]
        qs.filter.return_value = filtered

        response = self.client.get(f"{self.base}/agent/", {"status": "online"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        qs.filter.assert_called_once()

    @with_internal_auth
    def test_agents_totals(self):
        response = self.client.get(f"{self.base}/agents_totals/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("online", response.data)
        self.assertIn("offline", response.data)
        self.assertIn("custom_breaks", response.data)

    @with_internal_auth
    def test_agents_totals_with_status_filter(self):
        response = self.client.get(
            f"{self.base}/agents_totals/", {"status": "online"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("online", response.data)
        self.assertNotIn("offline", response.data)

    @with_internal_auth
    @patch(
        "chats.apps.api.v1.internal.dashboard.viewsets.AgentsService.get_agents_custom_status_and_rooms"
    )
    def test_custom_status_agent(self, mock_custom):
        mock_custom.return_value = [
            {
                "email": "agent@test.com",
                "first_name": "A",
                "last_name": "B",
                "status": "OFFLINE",
                "opened": 0,
                "closed": 1,
                "custom_status": [],
            }
        ]
        response = self.client.get(f"{self.base}/custom_status_agent/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
