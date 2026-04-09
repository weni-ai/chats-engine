from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.agents.views import AllAgentsView
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import CustomStatus, CustomStatusType
from chats.apps.queues.models import QueueAuthorization


def _make_manager(project):
    user = User.objects.create_user(email="manager@test.com", password="x")
    ProjectPermission.objects.create(
        project=project, user=user, role=ProjectPermission.ROLE_ADMIN
    )
    return user


def _make_agent(project, email, first_name, agent_status):
    user = User.objects.create_user(email=email, password="x", first_name=first_name)
    ProjectPermission.objects.create(
        project=project,
        user=user,
        role=ProjectPermission.ROLE_ATTENDANT,
        status=agent_status,
    )
    return user


def _put_on_pause(user, project, pause_name="Lunch"):
    status_type, _ = CustomStatusType.objects.get_or_create(
        name=pause_name, project=project
    )
    return CustomStatus.objects.create(
        user=user, status_type=status_type, is_active=True
    )


# ===========================================================================
# ENGAGE-7555 — Agent ordering by status and name
# Order: ONLINE → pause (active custom status) → OFFLINE, alphabetical within
# ===========================================================================


class AgentListOrderingTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.manager = _make_manager(self.project)

    def _list(self, extra_params=None):
        view = AllAgentsView.as_view()
        params = extra_params or {}
        request = self.factory.get(f"/project/{self.project.pk}/all_agents/", params)
        force_authenticate(request, user=self.manager)
        return view(request, project_uuid=str(self.project.pk))

    def _statuses(self, response):
        results = response.data.get("results", response.data)
        return [item["agent"]["chats_limit"]["active"] for item in results]

    def _status_values(self, response):
        """Return raw ProjectPermission status from the DB, ordered as returned."""
        results = response.data.get("results", response.data)
        emails = [item["email"] for item in results]
        perms = {
            p.user.email: p.status
            for p in ProjectPermission.objects.filter(
                project=self.project,
                user__email__in=emails,
            ).select_related("user")
        }
        return [perms[e] for e in emails]

    def _names(self, response):
        results = response.data.get("results", response.data)
        return [item["agent"]["name"].strip() for item in results]

    # ------------------------------------------------------------------
    # Case 20
    # ------------------------------------------------------------------

    def test_online_agents_appear_first(self):
        """ONLINE agents appear first in the listing."""
        _make_agent(
            self.project,
            "offline@test.com",
            "Offline",
            ProjectPermission.STATUS_OFFLINE,
        )
        _make_agent(
            self.project, "online@test.com", "Online", ProjectPermission.STATUS_ONLINE
        )

        response = self._list()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statuses = self._status_values(response)
        self.assertEqual(statuses[0], ProjectPermission.STATUS_ONLINE)

    # ------------------------------------------------------------------
    # Case 21
    # ------------------------------------------------------------------

    def test_paused_agents_appear_between_online_and_offline(self):
        """Agents with an active custom status appear after ONLINE and before OFFLINE."""
        offline_user = _make_agent(
            self.project,
            "offline@test.com",
            "Offline",
            ProjectPermission.STATUS_OFFLINE,
        )
        online_user = _make_agent(
            self.project, "online@test.com", "Online", ProjectPermission.STATUS_ONLINE
        )
        paused_user = _make_agent(
            self.project, "paused@test.com", "Paused", ProjectPermission.STATUS_ONLINE
        )
        _put_on_pause(paused_user, self.project)

        response = self._list()

        statuses = self._status_values(response)
        emails = [item["email"] for item in response.data.get("results", response.data)]

        self.assertEqual(emails[0], online_user.email)
        self.assertEqual(emails[1], paused_user.email)
        self.assertEqual(emails[2], offline_user.email)

    # ------------------------------------------------------------------
    # Case 22
    # ------------------------------------------------------------------

    def test_offline_agents_appear_last(self):
        """OFFLINE agents appear last in the listing."""
        _make_agent(
            self.project, "online@test.com", "Online", ProjectPermission.STATUS_ONLINE
        )
        _make_agent(
            self.project,
            "offline@test.com",
            "Offline",
            ProjectPermission.STATUS_OFFLINE,
        )

        response = self._list()

        statuses = self._status_values(response)
        self.assertEqual(statuses[-1], ProjectPermission.STATUS_OFFLINE)

    # ------------------------------------------------------------------
    # Case 23
    # ------------------------------------------------------------------

    def test_same_status_ordered_alphabetically_by_name(self):
        """Agents with the same status are ordered alphabetically by first name."""
        _make_agent(
            self.project, "zara@test.com", "Zara", ProjectPermission.STATUS_ONLINE
        )
        _make_agent(
            self.project, "ana@test.com", "Ana", ProjectPermission.STATUS_ONLINE
        )

        response = self._list()

        names = self._names(response)
        self.assertEqual(names, sorted(names))

    # ------------------------------------------------------------------
    # Case 24
    # ------------------------------------------------------------------

    def test_full_ordering_with_all_statuses_and_mixed_names(self):
        """Full ordering: ONLINE → pause → OFFLINE, each group sorted alphabetically."""
        _make_agent(
            self.project,
            "zara.online@test.com",
            "Zara",
            ProjectPermission.STATUS_ONLINE,
        )
        _make_agent(
            self.project, "ana.online@test.com", "Ana", ProjectPermission.STATUS_ONLINE
        )
        paused = _make_agent(
            self.project, "paused@test.com", "Marcus", ProjectPermission.STATUS_ONLINE
        )
        _put_on_pause(paused, self.project)
        _make_agent(
            self.project,
            "zara.offline@test.com",
            "Zara",
            ProjectPermission.STATUS_OFFLINE,
        )
        _make_agent(
            self.project,
            "ana.offline@test.com",
            "Ana",
            ProjectPermission.STATUS_OFFLINE,
        )

        response = self._list()
        emails = [item["email"] for item in response.data.get("results", response.data)]
        names = self._names(response)

        # Two ONLINE first (alphabetical)
        self.assertIn("ana.online@test.com", emails[:2])
        self.assertIn("zara.online@test.com", emails[:2])
        self.assertEqual(names[:2], sorted(names[:2]))
        # Paused in the middle
        self.assertEqual(emails[2], paused.email)
        # Two OFFLINE last (alphabetical)
        self.assertIn("ana.offline@test.com", emails[3:])
        self.assertIn("zara.offline@test.com", emails[3:])
        self.assertEqual(names[3:], sorted(names[3:]))


# ===========================================================================
# ENGAGE-7556 — Agent list filters
# Filters: status, custom_status, agent (email), sector, queue
# ===========================================================================


class AgentListFilterTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.manager = _make_manager(self.project)

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

    def _list(self, extra_params=None):
        view = AllAgentsView.as_view()
        request = self.factory.get(
            f"/project/{self.project.pk}/all_agents/",
            extra_params or {},
        )
        force_authenticate(request, user=self.manager)
        return view(request, project_uuid=str(self.project.pk))

    def _emails(self, response):
        results = response.data.get("results", response.data)
        return {item["email"] for item in results}

    # ------------------------------------------------------------------
    # Case 25
    # ------------------------------------------------------------------

    def test_filter_by_online_status_returns_only_online_agents(self):
        """Filter status=online returns only agents that are ONLINE without a pause."""
        response = self._list({"status": "online"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertNotIn(self.offline_user.email, emails)

    # ------------------------------------------------------------------
    # Case 26
    # ------------------------------------------------------------------

    def test_filter_by_offline_status_returns_only_offline_agents(self):
        """Filter status=offline returns only agents that are OFFLINE."""
        response = self._list({"status": "offline"})

        emails = self._emails(response)
        self.assertIn(self.offline_user.email, emails)
        self.assertNotIn(self.online_user.email, emails)

    # ------------------------------------------------------------------
    # Case 26b
    # ------------------------------------------------------------------

    def test_filter_by_custom_status_returns_paused_agents(self):
        """Filter custom_status=Lunch returns only agents currently on that pause."""
        _put_on_pause(self.online_user, self.project, "Lunch")

        response = self._list({"custom_status": "Lunch"})

        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertNotIn(self.offline_user.email, emails)

    # ------------------------------------------------------------------
    # Case 27
    # ------------------------------------------------------------------

    def test_filter_by_agent_email_returns_matching_agents(self):
        """Filter by agent email (partial match) returns only matching agents."""
        response = self._list({"agent": "online"})

        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertNotIn(self.offline_user.email, emails)

    # ------------------------------------------------------------------
    # Case 28
    # ------------------------------------------------------------------

    def test_filter_by_sector_returns_only_agents_in_that_sector(self):
        """Filter by sector returns only agents authorised in that sector."""
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
            permission=other_perm, queue=other_queue, role=QueueAuthorization.ROLE_AGENT
        )

        response = self._list({"sector": str(self.sector.pk)})

        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertIn(self.offline_user.email, emails)
        self.assertNotIn(other_user.email, emails)

    # ------------------------------------------------------------------
    # Case 29
    # ------------------------------------------------------------------

    def test_filter_by_queue_returns_only_agents_in_that_queue(self):
        """Filter by queue returns only agents authorised in that queue."""
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

        response = self._list({"queue": str(self.queue.pk)})

        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertIn(self.offline_user.email, emails)
        self.assertNotIn(other_user.email, emails)

    # ------------------------------------------------------------------
    # Case 30
    # ------------------------------------------------------------------

    def test_combined_filters_status_and_queue(self):
        """Combining status and queue filters works correctly."""
        response = self._list({"status": "online", "queue": str(self.queue.pk)})

        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertNotIn(self.offline_user.email, emails)

    # ------------------------------------------------------------------
    # Case 31
    # ------------------------------------------------------------------

    def test_no_extra_filters_returns_all_project_agents(self):
        """Without extra filters, returns all attendant agents in the project."""
        response = self._list()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertIn(self.offline_user.email, emails)
