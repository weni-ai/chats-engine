from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.agents.viewsets import AgentListViewset
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import QueueAuthorization


def _make_mock_redis():
    return MagicMock(**{"get.return_value": None, "set.return_value": None})


def _make_module_perm():
    content_type = ContentType.objects.get_for_model(User)
    perm, _ = Permission.objects.get_or_create(
        codename="can_communicate_internally",
        content_type=content_type,
    )
    return perm


# ===========================================================================
# ENGAGE-7555 — Agent ordering by status and name
# Order: ONLINE → pause (AWAY/BUSY) → OFFLINE; alphabetical within each group
# ===========================================================================


class AgentListOrderingTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.module_perm = _make_module_perm()

        self.internal_user = User.objects.create_user(
            email="internal@module.com", password="x"
        )
        self.internal_user.user_permissions.add(self.module_perm)

        self.project = Project.objects.create(name="Test Project", timezone="UTC")

    def _create_agent(self, email, first_name, agent_status):
        user = User.objects.create_user(
            email=email, password="x", first_name=first_name
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=agent_status,
        )
        return user

    def _list_agents(self, mock_redis):
        mock_redis.return_value = _make_mock_redis()
        view = AgentListViewset.as_view({"get": "list"})
        request = self.factory.get(f"/internal/agents/?project={self.project.pk}")
        force_authenticate(request, user=self.internal_user)
        return view(request)

    def _statuses(self, response):
        results = response.data.get("results", response.data)
        return [item["status"] for item in results]

    def _names(self, response):
        results = response.data.get("results", response.data)
        return [item["user"]["first_name"] for item in results]

    # ------------------------------------------------------------------
    # Case 20
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_online_agents_appear_first(self, mock_redis):
        """ONLINE agents appear first in the listing."""
        self._create_agent("offline@test.com", "Offline", ProjectPermission.STATUS_OFFLINE)
        self._create_agent("online@test.com", "Online", ProjectPermission.STATUS_ONLINE)

        response = self._list_agents(mock_redis)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._statuses(response)[0], ProjectPermission.STATUS_ONLINE)

    # ------------------------------------------------------------------
    # Case 21
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_away_agents_appear_between_online_and_offline(self, mock_redis):
        """AWAY agents appear after ONLINE and before OFFLINE agents."""
        self._create_agent("offline@test.com", "Offline", ProjectPermission.STATUS_OFFLINE)
        self._create_agent("away@test.com", "Away", ProjectPermission.STATUS_AWAY)
        self._create_agent("online@test.com", "Online", ProjectPermission.STATUS_ONLINE)

        response = self._list_agents(mock_redis)

        statuses = self._statuses(response)
        self.assertEqual(statuses[0], ProjectPermission.STATUS_ONLINE)
        self.assertEqual(statuses[1], ProjectPermission.STATUS_AWAY)
        self.assertEqual(statuses[2], ProjectPermission.STATUS_OFFLINE)

    # ------------------------------------------------------------------
    # Case 22
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_offline_agents_appear_last(self, mock_redis):
        """OFFLINE agents appear last in the listing."""
        self._create_agent("online@test.com", "Online", ProjectPermission.STATUS_ONLINE)
        self._create_agent("offline@test.com", "Offline", ProjectPermission.STATUS_OFFLINE)

        response = self._list_agents(mock_redis)

        self.assertEqual(self._statuses(response)[-1], ProjectPermission.STATUS_OFFLINE)

    # ------------------------------------------------------------------
    # Case 23
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_same_status_ordered_alphabetically_by_name(self, mock_redis):
        """Agents with the same status are ordered alphabetically by name."""
        self._create_agent("zara@test.com", "Zara", ProjectPermission.STATUS_ONLINE)
        self._create_agent("ana@test.com", "Ana", ProjectPermission.STATUS_ONLINE)

        response = self._list_agents(mock_redis)

        names = self._names(response)
        self.assertEqual(names, sorted(names))

    # ------------------------------------------------------------------
    # Case 24
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_full_ordering_with_all_statuses_and_mixed_names(self, mock_redis):
        """Full ordering: ONLINE → AWAY/BUSY → OFFLINE, each group sorted alphabetically."""
        self._create_agent("zara.online@test.com", "Zara", ProjectPermission.STATUS_ONLINE)
        self._create_agent("ana.online@test.com", "Ana", ProjectPermission.STATUS_ONLINE)
        self._create_agent("busy@test.com", "Marcus", ProjectPermission.STATUS_BUSY)
        self._create_agent("away@test.com", "Carlos", ProjectPermission.STATUS_AWAY)
        self._create_agent("zara.offline@test.com", "Zara", ProjectPermission.STATUS_OFFLINE)
        self._create_agent("ana.offline@test.com", "Ana", ProjectPermission.STATUS_OFFLINE)

        response = self._list_agents(mock_redis)

        statuses = self._statuses(response)
        names = self._names(response)
        pause_statuses = {ProjectPermission.STATUS_AWAY, ProjectPermission.STATUS_BUSY}

        # Two ONLINE first
        self.assertEqual(statuses[0], ProjectPermission.STATUS_ONLINE)
        self.assertEqual(statuses[1], ProjectPermission.STATUS_ONLINE)
        # Two pause statuses in the middle
        self.assertIn(statuses[2], pause_statuses)
        self.assertIn(statuses[3], pause_statuses)
        # Two OFFLINE last
        self.assertEqual(statuses[4], ProjectPermission.STATUS_OFFLINE)
        self.assertEqual(statuses[5], ProjectPermission.STATUS_OFFLINE)
        # Each group sorted alphabetically
        self.assertEqual(names[:2], sorted(names[:2]))
        self.assertEqual(names[4:], sorted(names[4:]))


# ===========================================================================
# ENGAGE-7556 — Agent list filters
# Filters: status, attendant (name/email), sector, queue
# ===========================================================================


class AgentListFilterTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.module_perm = _make_module_perm()

        self.internal_user = User.objects.create_user(
            email="internal@module.com", password="x"
        )
        self.internal_user.user_permissions.add(self.module_perm)

        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = self.project.sectors.create(
            name="Support", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.queue = self.sector.queues.create(name="Queue 1")

        self.online_user = User.objects.create_user(
            email="online@test.com", password="x", first_name="Ana"
        )
        self.offline_user = User.objects.create_user(
            email="offline@test.com", password="x", first_name="Carlos"
        )
        self.online_perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.online_user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )
        self.offline_perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.offline_user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_OFFLINE,
        )
        QueueAuthorization.objects.create(
            permission=self.online_perm,
            queue=self.queue,
            role=QueueAuthorization.ROLE_AGENT,
        )
        QueueAuthorization.objects.create(
            permission=self.offline_perm,
            queue=self.queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

    def _list_agents(self, mock_redis, extra_filters=""):
        mock_redis.return_value = _make_mock_redis()
        view = AgentListViewset.as_view({"get": "list"})
        request = self.factory.get(
            f"/internal/agents/?project={self.project.pk}{extra_filters}"
        )
        force_authenticate(request, user=self.internal_user)
        return view(request)

    def _emails(self, response):
        results = response.data.get("results", response.data)
        return {item["user"]["email"] for item in results}

    # ------------------------------------------------------------------
    # Case 25
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_filter_by_online_status_returns_only_online_agents(self, mock_redis):
        """Filter status=ONLINE returns only online agents."""
        response = self._list_agents(
            mock_redis, f"&status={ProjectPermission.STATUS_ONLINE}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertNotIn(self.offline_user.email, emails)

    # ------------------------------------------------------------------
    # Case 26
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_filter_by_offline_status_returns_only_offline_agents(self, mock_redis):
        """Filter status=OFFLINE returns only offline agents."""
        response = self._list_agents(
            mock_redis, f"&status={ProjectPermission.STATUS_OFFLINE}"
        )

        emails = self._emails(response)
        self.assertIn(self.offline_user.email, emails)
        self.assertNotIn(self.online_user.email, emails)

    # ------------------------------------------------------------------
    # Case 27
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_filter_by_attendant_name_returns_matching_agents(self, mock_redis):
        """Filter by attendant name returns only matching agents."""
        response = self._list_agents(mock_redis, "&attendant=Ana")

        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertNotIn(self.offline_user.email, emails)

    # ------------------------------------------------------------------
    # Case 28
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_filter_by_sector_returns_only_agents_in_that_sector(self, mock_redis):
        """Filter by sector returns only agents authorized in that sector."""
        other_sector = self.project.sectors.create(
            name="Other Sector", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        other_queue = other_sector.queues.create(name="Other Queue")
        other_user = User.objects.create_user(email="other@test.com", password="x")
        other_perm = ProjectPermission.objects.create(
            project=self.project,
            user=other_user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            permission=other_perm,
            queue=other_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        response = self._list_agents(mock_redis, f"&sector={self.sector.pk}")

        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertIn(self.offline_user.email, emails)
        self.assertNotIn(other_user.email, emails)

    # ------------------------------------------------------------------
    # Case 29
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_filter_by_queue_returns_only_agents_in_that_queue(self, mock_redis):
        """Filter by queue returns only agents authorized in that queue."""
        second_queue = self.sector.queues.create(name="Queue 2")
        other_user = User.objects.create_user(email="other@test.com", password="x")
        other_perm = ProjectPermission.objects.create(
            project=self.project,
            user=other_user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            permission=other_perm,
            queue=second_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        response = self._list_agents(mock_redis, f"&queue={self.queue.pk}")

        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertIn(self.offline_user.email, emails)
        self.assertNotIn(other_user.email, emails)

    # ------------------------------------------------------------------
    # Case 30
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_combined_filters_status_and_queue(self, mock_redis):
        """Combining status and queue filters works correctly."""
        response = self._list_agents(
            mock_redis,
            f"&status={ProjectPermission.STATUS_ONLINE}&queue={self.queue.pk}",
        )

        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertNotIn(self.offline_user.email, emails)

    # ------------------------------------------------------------------
    # Case 31
    # ------------------------------------------------------------------

    @patch("chats.apps.api.v1.internal.permissions.get_redis_connection")
    def test_no_extra_filters_returns_all_project_agents(self, mock_redis):
        """Without extra filters, returns all agents in the project."""
        response = self._list_agents(mock_redis)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertIn(self.offline_user.email, emails)
