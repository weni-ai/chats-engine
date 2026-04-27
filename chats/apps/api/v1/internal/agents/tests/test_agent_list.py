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
        emails = [item["agent"]["email"] for item in results]
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

        emails = [item["agent"]["email"] for item in response.data.get("results", response.data)]

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
        emails = [item["agent"]["email"] for item in response.data.get("results", response.data)]
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
# Filters: status (online, offline, or custom pause name), agent (email), sector, queue
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
        request.resolver_match = type(
            "ResolverMatch", (), {"kwargs": {"project_uuid": str(self.project.pk)}}
        )()
        return view(request, project_uuid=str(self.project.pk))

    def _emails(self, response):
        results = response.data.get("results", response.data)
        return {item["agent"]["email"] for item in results}

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

    def test_filter_status_accepts_custom_pause_name(self):
        """Filter status=<custom pause name> returns only agents currently on that pause."""
        _put_on_pause(self.online_user, self.project, "Pré-pausa")

        response = self._list({"status": "Pré-pausa"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = self._emails(response)
        self.assertEqual(emails, {self.online_user.email})

    def test_filter_status_combines_online_and_custom_pause(self):
        """status=online,Pré-pausa returns ONLINE agents (without pause) plus agents on that pause."""
        paused_user = User.objects.create_user(
            email="paused@test.com", password="x", first_name="Paused"
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=paused_user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )
        _put_on_pause(paused_user, self.project, "Pré-pausa")

        response = self._list({"status": "online,Pré-pausa"})

        emails = self._emails(response)
        self.assertIn(self.online_user.email, emails)
        self.assertIn(paused_user.email, emails)
        self.assertNotIn(self.offline_user.email, emails)

    def test_filter_status_custom_name_scoped_to_project(self):
        """Custom pause status filter does not match active pauses from other projects."""
        other_project = Project.objects.create(name="Other", timezone="UTC")
        _put_on_pause(self.online_user, other_project, "Pré-pausa")

        response = self._list({"status": "Pré-pausa"})

        emails = self._emails(response)
        self.assertNotIn(self.online_user.email, emails)
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


# ===========================================================================
# ENGAGE-7672 — Response structure: sector, sector_chats_total_limit, email
# ===========================================================================


class AgentListResponseStructureTests(TestCase):
    """Validates the new response structure with sector details and sector_chats_total_limit."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.manager = _make_manager(self.project)

        self.sector_a = self.project.sectors.create(
            name="Support", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.sector_b = self.project.sectors.create(
            name="Sales", rooms_limit=3, work_start="08:00", work_end="18:00"
        )
        self.queue_a1 = self.sector_a.queues.create(name="Queue A1")
        self.queue_a2 = self.sector_a.queues.create(name="Queue A2")
        self.queue_b1 = self.sector_b.queues.create(name="Queue B1")

        self.agent_user = User.objects.create_user(
            email="agent@test.com", password="x", first_name="Ana", last_name="Silva"
        )
        self.agent_perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent_user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )
        QueueAuthorization.objects.create(
            permission=self.agent_perm,
            queue=self.queue_a1,
            role=QueueAuthorization.ROLE_AGENT,
        )
        QueueAuthorization.objects.create(
            permission=self.agent_perm,
            queue=self.queue_a2,
            role=QueueAuthorization.ROLE_AGENT,
        )
        QueueAuthorization.objects.create(
            permission=self.agent_perm,
            queue=self.queue_b1,
            role=QueueAuthorization.ROLE_AGENT,
        )

    def _list(self):
        view = AllAgentsView.as_view()
        request = self.factory.get(f"/project/{self.project.pk}/all_agents/")
        force_authenticate(request, user=self.manager)
        return view(request, project_uuid=str(self.project.pk))

    def _agent_data(self, response, email):
        results = response.data.get("results", response.data)
        return next(item["agent"] for item in results if item["agent"]["email"] == email)

    # ------------------------------------------------------------------
    # Case 32
    # ------------------------------------------------------------------

    def test_email_is_inside_agent_object(self):
        """The email field is nested inside the agent object."""
        response = self._list()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        first_item = results[0]
        self.assertIn("email", first_item["agent"])
        self.assertNotIn("email", first_item)

    # ------------------------------------------------------------------
    # Case 33
    # ------------------------------------------------------------------

    def test_sector_auth_no_longer_in_response(self):
        """The old sector_auth field is no longer present in the response."""
        response = self._list()

        results = response.data.get("results", response.data)
        first_item = results[0]
        self.assertNotIn("sector_auth", first_item)

    # ------------------------------------------------------------------
    # Case 34
    # ------------------------------------------------------------------

    def test_sector_lists_sectors_with_queue_names(self):
        """The sector field returns sector objects with name and list of queue names."""
        response = self._list()

        agent = self._agent_data(response, self.agent_user.email)
        sector_names = {s["name"] for s in agent["sector"]}
        self.assertEqual(sector_names, {"Support", "Sales"})

        support = next(s for s in agent["sector"] if s["name"] == "Support")
        self.assertEqual(sorted(support["queues"]), ["Queue A1", "Queue A2"])

        sales = next(s for s in agent["sector"] if s["name"] == "Sales")
        self.assertEqual(sales["queues"], ["Queue B1"])

    # ------------------------------------------------------------------
    # Case 35
    # ------------------------------------------------------------------

    def test_sector_only_shows_authorized_queues(self):
        """Agent's sector only includes queues the agent is authorized in."""
        self.sector_a.queues.create(name="Queue A3 (not authorized)")

        response = self._list()

        agent = self._agent_data(response, self.agent_user.email)
        support = next(s for s in agent["sector"] if s["name"] == "Support")
        self.assertNotIn("Queue A3 (not authorized)", support["queues"])
        self.assertEqual(sorted(support["queues"]), ["Queue A1", "Queue A2"])

    # ------------------------------------------------------------------
    # Case 36
    # ------------------------------------------------------------------

    def test_sector_chats_total_limit_sums_rooms_limit_from_all_sectors(self):
        """sector_chats_total_limit returns the sum of rooms_limit across all agent sectors."""
        response = self._list()

        agent = self._agent_data(response, self.agent_user.email)
        # Support (5) + Sales (3) = 8
        self.assertEqual(agent["sector_chats_total_limit"], 8)

    # ------------------------------------------------------------------
    # Case 37
    # ------------------------------------------------------------------

    def test_sector_chats_total_limit_with_single_sector(self):
        """sector_chats_total_limit returns just the one sector's limit when agent has one sector."""
        single_user = User.objects.create_user(
            email="single@test.com", password="x", first_name="Bob"
        )
        single_perm = ProjectPermission.objects.create(
            project=self.project,
            user=single_user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )
        QueueAuthorization.objects.create(
            permission=single_perm,
            queue=self.queue_b1,
            role=QueueAuthorization.ROLE_AGENT,
        )

        response = self._list()

        agent = self._agent_data(response, single_user.email)
        self.assertEqual(agent["sector_chats_total_limit"], 3)

    # ------------------------------------------------------------------
    # Case 38
    # ------------------------------------------------------------------

    def test_sector_chats_total_limit_zero_when_no_queues(self):
        """sector_chats_total_limit is 0 when agent has no queue authorizations."""
        lonely_user = User.objects.create_user(
            email="lonely@test.com", password="x", first_name="Lonely"
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=lonely_user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )

        response = self._list()

        agent = self._agent_data(response, lonely_user.email)
        self.assertEqual(agent["sector_chats_total_limit"], 0)
        self.assertEqual(agent["sector"], [])

    # ------------------------------------------------------------------
    # Case 39
    # ------------------------------------------------------------------

    def test_sector_does_not_duplicate_when_multiple_queues_in_same_sector(self):
        """A sector appears only once even if the agent has multiple queues in it."""
        response = self._list()

        agent = self._agent_data(response, self.agent_user.email)
        support_entries = [s for s in agent["sector"] if s["name"] == "Support"]
        self.assertEqual(len(support_entries), 1)

    # ------------------------------------------------------------------
    # Case 40
    # ------------------------------------------------------------------

    def test_chats_limit_independent_of_sector_chats_total_limit(self):
        """chats_limit reflects the custom per-agent config, independent of sector totals."""
        self.agent_perm.is_custom_limit_active = True
        self.agent_perm.custom_rooms_limit = 20
        self.agent_perm.save(
            update_fields=["is_custom_limit_active", "custom_rooms_limit"]
        )

        response = self._list()

        agent = self._agent_data(response, self.agent_user.email)
        self.assertEqual(agent["chats_limit"]["active"], True)
        self.assertEqual(agent["chats_limit"]["total"], 20)
        # sector total remains the sum of sector limits, unaffected
        self.assertEqual(agent["sector_chats_total_limit"], 8)

    # ------------------------------------------------------------------
    # Case 41
    # ------------------------------------------------------------------

    def test_sector_chats_total_limit_does_not_double_count_sector(self):
        """A sector's rooms_limit is counted once even with multiple queues authorized."""
        response = self._list()

        agent = self._agent_data(response, self.agent_user.email)
        # Agent has 2 queues in Support but rooms_limit=5 counted once
        self.assertEqual(agent["sector_chats_total_limit"], 8)

    # ------------------------------------------------------------------
    # Case 42
    # ------------------------------------------------------------------

    def test_chats_limit_total_falls_back_to_sector_sum_when_no_custom_limit(self):
        """When no custom limit is configured, chats_limit.total returns the sector sum."""
        response = self._list()

        agent = self._agent_data(response, self.agent_user.email)
        self.assertFalse(agent["chats_limit"]["active"])
        # Support (5) + Sales (3) = 8 — same as sector_chats_total_limit
        self.assertEqual(agent["chats_limit"]["total"], 8)
        self.assertEqual(
            agent["chats_limit"]["total"], agent["sector_chats_total_limit"]
        )

    # ------------------------------------------------------------------
    # Case 43
    # ------------------------------------------------------------------

    def test_chats_limit_total_falls_back_when_active_but_total_is_null(self):
        """If is_custom_limit_active=True but custom_rooms_limit is None, falls back to sector sum."""
        self.agent_perm.is_custom_limit_active = True
        self.agent_perm.custom_rooms_limit = None
        self.agent_perm.save(
            update_fields=["is_custom_limit_active", "custom_rooms_limit"]
        )

        response = self._list()

        agent = self._agent_data(response, self.agent_user.email)
        self.assertTrue(agent["chats_limit"]["active"])
        self.assertEqual(agent["chats_limit"]["total"], 8)

    # ------------------------------------------------------------------
    # Case 44
    # ------------------------------------------------------------------

    def test_chats_limit_total_is_zero_when_no_custom_and_no_sectors(self):
        """Agent without custom limit and without sectors returns total=0 (sum of empty set)."""
        lonely_user = User.objects.create_user(
            email="lonely-limit@test.com", password="x", first_name="Lonely"
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=lonely_user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )

        response = self._list()

        agent = self._agent_data(response, lonely_user.email)
        self.assertFalse(agent["chats_limit"]["active"])
        self.assertEqual(agent["chats_limit"]["total"], 0)


# ===========================================================================
# ENGAGE-7672 — Status field: "online" | "offline" | pause name
# ===========================================================================


class AgentListStatusFieldTests(TestCase):
    """Validates the `status` field returned for each agent."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.manager = _make_manager(self.project)

    def _list(self):
        view = AllAgentsView.as_view()
        request = self.factory.get(f"/project/{self.project.pk}/all_agents/")
        force_authenticate(request, user=self.manager)
        return view(request, project_uuid=str(self.project.pk))

    def _agent_data(self, response, email):
        results = response.data.get("results", response.data)
        return next(
            item["agent"] for item in results if item["agent"]["email"] == email
        )

    # ------------------------------------------------------------------
    # Case 45
    # ------------------------------------------------------------------

    def test_status_is_online_for_online_agent_without_pause(self):
        """An ONLINE agent without any active pause returns status='online'."""
        user = _make_agent(
            self.project, "online@test.com", "Ana", ProjectPermission.STATUS_ONLINE
        )

        response = self._list()

        agent = self._agent_data(response, user.email)
        self.assertEqual(agent["status"], "online")

    # ------------------------------------------------------------------
    # Case 46
    # ------------------------------------------------------------------

    def test_status_is_offline_for_offline_agent(self):
        """An OFFLINE agent returns status='offline'."""
        user = _make_agent(
            self.project,
            "offline@test.com",
            "Bob",
            ProjectPermission.STATUS_OFFLINE,
        )

        response = self._list()

        agent = self._agent_data(response, user.email)
        self.assertEqual(agent["status"], "offline")

    # ------------------------------------------------------------------
    # Case 47
    # ------------------------------------------------------------------

    def test_status_returns_pause_name_for_paused_agent(self):
        """An agent on pause returns the pause name in the status field."""
        user = _make_agent(
            self.project, "paused@test.com", "Carla", ProjectPermission.STATUS_ONLINE
        )
        _put_on_pause(user, self.project, pause_name="Lunch")

        response = self._list()

        agent = self._agent_data(response, user.email)
        self.assertEqual(agent["status"], "Lunch")

    # ------------------------------------------------------------------
    # Case 48
    # ------------------------------------------------------------------

    def test_status_pause_wins_over_online(self):
        """Pause name takes precedence over ONLINE status."""
        user = _make_agent(
            self.project, "paused@test.com", "Dan", ProjectPermission.STATUS_ONLINE
        )
        _put_on_pause(user, self.project, pause_name="Break")

        response = self._list()

        agent = self._agent_data(response, user.email)
        self.assertEqual(agent["status"], "Break")
        self.assertNotEqual(agent["status"], "online")

    # ------------------------------------------------------------------
    # Case 49
    # ------------------------------------------------------------------

    def test_status_ignores_in_service_custom_status(self):
        """CustomStatus 'in-service' does NOT appear as status — falls back to online/offline."""
        user = _make_agent(
            self.project,
            "in-service@test.com",
            "Eve",
            ProjectPermission.STATUS_ONLINE,
        )
        _put_on_pause(user, self.project, pause_name="in-service")

        response = self._list()

        agent = self._agent_data(response, user.email)
        self.assertEqual(agent["status"], "online")

    # ------------------------------------------------------------------
    # Case 50
    # ------------------------------------------------------------------

    def test_status_in_service_is_case_insensitive(self):
        """The 'in-service' exclusion is case-insensitive."""
        user = _make_agent(
            self.project,
            "in-service-upper@test.com",
            "Frank",
            ProjectPermission.STATUS_ONLINE,
        )
        _put_on_pause(user, self.project, pause_name="In-Service")

        response = self._list()

        agent = self._agent_data(response, user.email)
        self.assertEqual(agent["status"], "online")

    # ------------------------------------------------------------------
    # Case 51
    # ------------------------------------------------------------------

    def test_status_field_present_for_all_agents(self):
        """All agents in the response include the status field."""
        _make_agent(
            self.project, "online@test.com", "Ana", ProjectPermission.STATUS_ONLINE
        )
        _make_agent(
            self.project,
            "offline@test.com",
            "Bob",
            ProjectPermission.STATUS_OFFLINE,
        )
        paused = _make_agent(
            self.project, "paused@test.com", "Carla", ProjectPermission.STATUS_ONLINE
        )
        _put_on_pause(paused, self.project, pause_name="Lunch")

        response = self._list()

        results = response.data.get("results", response.data)
        for item in results:
            self.assertIn("status", item["agent"])
            self.assertIsNotNone(item["agent"]["status"])


# ===========================================================================
# Agent list filters — multi-value support (comma-separated)
# ===========================================================================


class AgentListMultiValueFilterTests(TestCase):
    """Validates that all filters accept multiple comma-separated values."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.manager = _make_manager(self.project)

        self.sector_a = self.project.sectors.create(
            name="Sector A", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.sector_b = self.project.sectors.create(
            name="Sector B", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.sector_c = self.project.sectors.create(
            name="Sector C", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.queue_a = self.sector_a.queues.create(name="Queue A")
        self.queue_b = self.sector_b.queues.create(name="Queue B")
        self.queue_c = self.sector_c.queues.create(name="Queue C")

        self.user_a = _make_agent(
            self.project, "agent.a@test.com", "Ana", ProjectPermission.STATUS_ONLINE
        )
        self.user_b = _make_agent(
            self.project, "agent.b@test.com", "Bob", ProjectPermission.STATUS_OFFLINE
        )
        self.user_c = _make_agent(
            self.project, "agent.c@test.com", "Carla", ProjectPermission.STATUS_ONLINE
        )

        for user, queue in [
            (self.user_a, self.queue_a),
            (self.user_b, self.queue_b),
            (self.user_c, self.queue_c),
        ]:
            QueueAuthorization.objects.create(
                permission=ProjectPermission.objects.get(user=user, project=self.project),
                queue=queue,
                role=QueueAuthorization.ROLE_AGENT,
            )

    def _list(self, extra_params=None):
        view = AllAgentsView.as_view()
        request = self.factory.get(
            f"/project/{self.project.pk}/all_agents/",
            extra_params or {},
        )
        force_authenticate(request, user=self.manager)
        request.resolver_match = type(
            "ResolverMatch", (), {"kwargs": {"project_uuid": str(self.project.pk)}}
        )()
        return view(request, project_uuid=str(self.project.pk))

    def _emails(self, response):
        results = response.data.get("results", response.data)
        return {item["agent"]["email"] for item in results}

    def test_filter_status_accepts_multiple_values(self):
        """status=online,offline returns both online and offline agents."""
        response = self._list({"status": "online,offline"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = self._emails(response)
        self.assertIn(self.user_a.email, emails)
        self.assertIn(self.user_b.email, emails)
        self.assertIn(self.user_c.email, emails)

    def test_filter_queue_accepts_multiple_uuids(self):
        """queue=uuid1,uuid2 returns agents from either queue."""
        response = self._list(
            {"queue": f"{self.queue_a.pk},{self.queue_b.pk}"}
        )

        emails = self._emails(response)
        self.assertIn(self.user_a.email, emails)
        self.assertIn(self.user_b.email, emails)
        self.assertNotIn(self.user_c.email, emails)

    def test_filter_sector_accepts_multiple_uuids(self):
        """sector=uuid1,uuid2 returns agents from either sector."""
        response = self._list(
            {"sector": f"{self.sector_a.pk},{self.sector_c.pk}"}
        )

        emails = self._emails(response)
        self.assertIn(self.user_a.email, emails)
        self.assertIn(self.user_c.email, emails)
        self.assertNotIn(self.user_b.email, emails)

    def test_filter_agent_accepts_multiple_values(self):
        """agent=a,c matches agents whose emails contain either token."""
        response = self._list({"agent": "agent.a,agent.c"})

        emails = self._emails(response)
        self.assertIn(self.user_a.email, emails)
        self.assertIn(self.user_c.email, emails)
        self.assertNotIn(self.user_b.email, emails)

    def test_filter_status_accepts_multiple_custom_pause_names(self):
        """status=Lunch,Break returns agents on either pause."""
        _put_on_pause(self.user_a, self.project, pause_name="Lunch")
        _put_on_pause(self.user_c, self.project, pause_name="Break")

        response = self._list({"status": "Lunch,Break"})

        emails = self._emails(response)
        self.assertIn(self.user_a.email, emails)
        self.assertIn(self.user_c.email, emails)
        self.assertNotIn(self.user_b.email, emails)


# ===========================================================================
# Bug fix — sectors without active queue authorizations should not appear
# Also: deleted sectors and queues should not appear
# ===========================================================================


class AgentListSectorVisibilityTests(TestCase):
    """
    Validates that the `sector` array only contains sectors in which the
    agent has at least one active queue authorization, and that deleted
    sectors/queues are filtered out.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.manager = _make_manager(self.project)

        self.agent_user = User.objects.create_user(
            email="agent@test.com", password="x", first_name="Ana"
        )
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent_user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )

    def _list(self):
        view = AllAgentsView.as_view()
        request = self.factory.get(f"/project/{self.project.pk}/all_agents/")
        force_authenticate(request, user=self.manager)
        return view(request, project_uuid=str(self.project.pk))

    def _agent_data(self, response):
        results = response.data.get("results", response.data)
        return next(
            item["agent"] for item in results
            if item["agent"]["email"] == self.agent_user.email
        )

    def test_sector_with_no_queue_auth_is_not_returned(self):
        """A sector where the agent has only SectorAuthorization (no QueueAuthorization) is hidden."""
        from chats.apps.sectors.models import SectorAuthorization

        empty_sector = self.project.sectors.create(
            name="Empty Sector", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        SectorAuthorization.objects.create(
            permission=self.permission, sector=empty_sector, role=1
        )

        response = self._list()

        agent = self._agent_data(response)
        sector_names = {s["name"] for s in agent["sector"]}
        self.assertNotIn("Empty Sector", sector_names)

    def test_deleted_sector_is_not_returned(self):
        """A sector flagged as deleted does not appear, even if agent has queue auth there."""
        deleted_sector = self.project.sectors.create(
            name="Deleted Sector",
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )
        deleted_queue = deleted_sector.queues.create(name="Deleted Queue")
        QueueAuthorization.objects.create(
            permission=self.permission,
            queue=deleted_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        active_sector = self.project.sectors.create(
            name="Active Sector",
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )
        active_queue = active_sector.queues.create(name="Active Queue")
        QueueAuthorization.objects.create(
            permission=self.permission,
            queue=active_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        deleted_sector.is_deleted = True
        deleted_sector.save(update_fields=["is_deleted"])

        response = self._list()

        agent = self._agent_data(response)
        sector_names = {s["name"] for s in agent["sector"]}
        self.assertNotIn("Deleted Sector", sector_names)
        self.assertIn("Active Sector", sector_names)

    def test_deleted_queue_is_not_returned_inside_sector(self):
        """A deleted queue does not show up in its sector's queue list."""
        sector = self.project.sectors.create(
            name="Sector", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        active_queue = sector.queues.create(name="Active Queue")
        deleted_queue = sector.queues.create(name="Deleted Queue")
        QueueAuthorization.objects.create(
            permission=self.permission,
            queue=active_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )
        QueueAuthorization.objects.create(
            permission=self.permission,
            queue=deleted_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        deleted_queue.is_deleted = True
        deleted_queue.save(update_fields=["is_deleted"])

        response = self._list()

        agent = self._agent_data(response)
        sector_entry = next(s for s in agent["sector"] if s["name"] == "Sector")
        self.assertIn("Active Queue", sector_entry["queues"])
        self.assertNotIn("Deleted Queue", sector_entry["queues"])

    def test_sector_with_only_deleted_queues_is_not_returned(self):
        """A sector whose only queues are deleted is hidden from the response."""
        sector = self.project.sectors.create(
            name="Only Deleted",
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )
        deleted_queue = sector.queues.create(name="Gone")
        QueueAuthorization.objects.create(
            permission=self.permission,
            queue=deleted_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )
        deleted_queue.is_deleted = True
        deleted_queue.save(update_fields=["is_deleted"])

        response = self._list()

        agent = self._agent_data(response)
        sector_names = {s["name"] for s in agent["sector"]}
        self.assertNotIn("Only Deleted", sector_names)

    def test_sector_chats_total_limit_excludes_hidden_sectors(self):
        """sector_chats_total_limit sums only visible (non-deleted, with active queues) sectors."""
        visible_sector = self.project.sectors.create(
            name="Visible",
            rooms_limit=7,
            work_start="08:00",
            work_end="18:00",
        )
        visible_queue = visible_sector.queues.create(name="Queue")
        QueueAuthorization.objects.create(
            permission=self.permission,
            queue=visible_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        # Another sector with deleted queue → should not count
        hidden_sector = self.project.sectors.create(
            name="Hidden",
            rooms_limit=100,
            work_start="08:00",
            work_end="18:00",
        )
        hidden_queue = hidden_sector.queues.create(name="Dead Queue")
        QueueAuthorization.objects.create(
            permission=self.permission,
            queue=hidden_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )
        hidden_queue.is_deleted = True
        hidden_queue.save(update_fields=["is_deleted"])

        response = self._list()

        agent = self._agent_data(response)
        self.assertEqual(agent["sector_chats_total_limit"], 7)
