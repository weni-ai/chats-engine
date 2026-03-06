from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import (
    AgentStatusLog,
    CustomStatus,
    CustomStatusType,
)
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


class BaseExternalAgentsStatusTest(APITestCase):
    url = "/v1/external/agents_status/"

    def setUp(self):
        self.project = Project.objects.create(name="Status Project")
        self.external_token = self.project.external_token

        self.agent_1 = User.objects.create(
            email="agent1@test.com",
            first_name="Agent",
            last_name="One",
            is_active=True,
        )
        self.agent_2 = User.objects.create(
            email="agent2@test.com",
            first_name="Agent",
            last_name="Two",
            is_active=True,
        )

        self.perm_1 = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent_1,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )
        self.perm_2 = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent_2,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_OFFLINE,
        )

        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Q1", sector=self.sector)

    def _auth(self, token_uuid=None):
        token = token_uuid or self.external_token.uuid
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _get(self, query_params=None):
        return self.client.get(self.url, query_params)

    def _get_results(self, response):
        return response.data.get("results", response.data)

    def _find_agent(self, response, email):
        results = self._get_results(response)
        return next(a for a in results if a["email"] == email)


class TestAgentsStatusUnauthenticated(BaseExternalAgentsStatusTest):
    def test_returns_401_without_token(self):
        response = self._get()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_401_with_invalid_token(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer 00000000-0000-0000-0000-000000000000"
        )
        response = self._get()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestAgentsStatusList(BaseExternalAgentsStatusTest):
    def test_lists_all_agents(self):
        self._auth()
        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._get_results(response)
        emails = {agent["email"] for agent in results}
        self.assertIn("agent1@test.com", emails)
        self.assertIn("agent2@test.com", emails)

    def test_returns_correct_status_fields(self):
        self._auth()
        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        agent_1_data = self._find_agent(response, "agent1@test.com")
        self.assertEqual(agent_1_data["status"], "ONLINE")
        self.assertEqual(agent_1_data["first_name"], "Agent")
        self.assertEqual(agent_1_data["last_name"], "One")
        self.assertIn("uuid", agent_1_data)
        self.assertIn("last_seen", agent_1_data)
        self.assertIn("last_status_change", agent_1_data)
        self.assertIn("time_in_current_status", agent_1_data)
        self.assertIn("active_custom_status", agent_1_data)

    def test_agent_without_custom_status_returns_null(self):
        self._auth()
        response = self._get()

        agent_data = self._find_agent(response, "agent1@test.com")
        self.assertIsNone(agent_data["active_custom_status"])

    def test_does_not_list_agents_from_other_project(self):
        other_project = Project.objects.create(name="Other Project")
        other_user = User.objects.create(email="other@test.com", is_active=True)
        ProjectPermission.objects.create(
            project=other_project,
            user=other_user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )

        self._auth()
        response = self._get()

        results = self._get_results(response)
        emails = {agent["email"] for agent in results}
        self.assertNotIn("other@test.com", emails)

    def test_does_not_list_users_with_no_role(self):
        no_role_user = User.objects.create(email="norole@test.com", is_active=True)
        ProjectPermission.objects.create(
            project=self.project,
            user=no_role_user,
            role=ProjectPermission.ROLE_NOT_SETTED,
        )

        self._auth()
        response = self._get()

        results = self._get_results(response)
        emails = {agent["email"] for agent in results}
        self.assertNotIn("norole@test.com", emails)


class TestAgentsStatusWithCustomStatus(BaseExternalAgentsStatusTest):
    def setUp(self):
        super().setUp()
        self.status_type = CustomStatusType.objects.create(
            name="Pausa-Almoço",
            project=self.project,
        )
        self.custom_status = CustomStatus.objects.create(
            user=self.agent_2,
            status_type=self.status_type,
            is_active=True,
        )

    def test_returns_active_custom_status(self):
        self._auth()
        response = self._get()

        agent_2_data = self._find_agent(response, "agent2@test.com")
        self.assertIsNotNone(agent_2_data["active_custom_status"])
        self.assertEqual(
            agent_2_data["active_custom_status"]["name"], "Pausa-Almoço"
        )
        self.assertIsNotNone(agent_2_data["active_custom_status"]["since"])

    def test_in_service_status_is_excluded(self):
        in_service_type = CustomStatusType.objects.create(
            name="In-Service",
            project=self.project,
        )
        self.custom_status.is_active = False
        self.custom_status.save()

        CustomStatus.objects.create(
            user=self.agent_1,
            status_type=in_service_type,
            is_active=True,
        )

        self._auth()
        response = self._get()

        agent_1_data = self._find_agent(response, "agent1@test.com")
        self.assertIsNone(agent_1_data["active_custom_status"])

    def test_inactive_custom_status_returns_null(self):
        self.custom_status.is_active = False
        self.custom_status.save()

        self._auth()
        response = self._get()

        agent_2_data = self._find_agent(response, "agent2@test.com")
        self.assertIsNone(agent_2_data["active_custom_status"])


class TestAgentsStatusWithStatusLog(BaseExternalAgentsStatusTest):
    def setUp(self):
        super().setUp()
        now = timezone.now()
        self.change_timestamp = (now - timedelta(minutes=30)).isoformat()

        AgentStatusLog.objects.create(
            agent=self.agent_1,
            project=self.project,
            log_date=now.date(),
            status_changes=[
                {
                    "timestamp": (now - timedelta(hours=2)).isoformat(),
                    "status": "ONLINE",
                    "custom_status": None,
                },
                {
                    "timestamp": self.change_timestamp,
                    "status": "ONLINE",
                    "custom_status": None,
                },
            ],
        )

    def test_returns_last_status_change_timestamp(self):
        self._auth()
        response = self._get()

        agent_1_data = self._find_agent(response, "agent1@test.com")
        self.assertEqual(
            agent_1_data["last_status_change"], self.change_timestamp
        )

    def test_returns_time_in_current_status_in_seconds(self):
        self._auth()
        response = self._get()

        agent_1_data = self._find_agent(response, "agent1@test.com")
        self.assertIsNotNone(agent_1_data["time_in_current_status"])
        self.assertGreater(agent_1_data["time_in_current_status"], 0)
        self.assertAlmostEqual(
            agent_1_data["time_in_current_status"], 30 * 60, delta=10
        )

    def test_agent_without_log_returns_null_for_status_change(self):
        self._auth()
        response = self._get()

        agent_2_data = self._find_agent(response, "agent2@test.com")
        self.assertIsNone(agent_2_data["last_status_change"])
        self.assertIsNone(agent_2_data["time_in_current_status"])


class TestAgentsStatusLastSeen(BaseExternalAgentsStatusTest):
    def test_returns_last_seen_when_set(self):
        now = timezone.now()
        self.perm_1.last_seen = now
        self.perm_1.save(update_fields=["last_seen"])

        self._auth()
        response = self._get()

        agent_1_data = self._find_agent(response, "agent1@test.com")
        self.assertIsNotNone(agent_1_data["last_seen"])

    def test_returns_null_last_seen_when_never_connected(self):
        self._auth()
        response = self._get()

        agent_1_data = self._find_agent(response, "agent1@test.com")
        self.assertIsNone(agent_1_data["last_seen"])


class TestAgentsStatusFilters(BaseExternalAgentsStatusTest):
    def setUp(self):
        super().setUp()
        self.queue_auth = self.queue.authorizations.create(
            permission=self.perm_1, role=1
        )

    def test_filter_by_queue(self):
        self._auth()
        response = self._get({"queue": str(self.queue.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_sector(self):
        self._auth()
        response = self._get({"sector": str(self.sector.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestAgentsStatusRetrieve(BaseExternalAgentsStatusTest):
    def test_retrieve_single_agent(self):
        self._auth()
        url = f"{self.url}{self.perm_1.uuid}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "agent1@test.com")
        self.assertEqual(response.data["status"], "ONLINE")

    def test_retrieve_agent_from_other_project_returns_404(self):
        other_project = Project.objects.create(name="Other")
        other_user = User.objects.create(email="x@test.com", is_active=True)
        other_perm = ProjectPermission.objects.create(
            project=other_project,
            user=other_user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self._auth()
        url = f"{self.url}{other_perm.uuid}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
