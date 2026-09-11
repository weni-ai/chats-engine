from datetime import time

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.api.v1.agents.filters import AllAgentsFilter
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import CustomStatus, CustomStatusType
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector


class AllAgentsFilterTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Filter Project")
        self.sector = Sector.objects.create(
            name="Sector A",
            project=self.project,
            rooms_limit=5,
            work_start=time(9, 0),
            work_end=time(18, 0),
        )
        self.other_sector = Sector.objects.create(
            name="Sector B",
            project=self.project,
            rooms_limit=5,
            work_start=time(9, 0),
            work_end=time(18, 0),
        )
        self.queue = Queue.objects.create(name="Queue A", sector=self.sector)
        self.other_queue = Queue.objects.create(
            name="Queue B", sector=self.other_sector
        )

        self.online_agent = self._make_agent(
            "online@test.com",
            "Ana",
            "Online",
            ProjectPermission.STATUS_ONLINE,
        )
        self.offline_agent = self._make_agent(
            "offline@test.com",
            "Bruno",
            "Offline",
            ProjectPermission.STATUS_OFFLINE,
        )
        self.paused_agent = self._make_agent(
            "paused@test.com",
            "Carla",
            "Paused",
            ProjectPermission.STATUS_ONLINE,
        )

        self.online_perm = ProjectPermission.objects.get(user=self.online_agent)
        self.offline_perm = ProjectPermission.objects.get(user=self.offline_agent)
        self.paused_perm = ProjectPermission.objects.get(user=self.paused_agent)

        pause_type = CustomStatusType.objects.create(
            name="Lunch",
            project=self.project,
        )
        CustomStatus.objects.create(
            user=self.paused_agent,
            status_type=pause_type,
            is_active=True,
        )

        QueueAuthorization.objects.create(
            permission=self.online_perm,
            queue=self.queue,
            role=QueueAuthorization.ROLE_AGENT,
        )
        QueueAuthorization.objects.create(
            permission=self.offline_perm,
            queue=self.other_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

    def _make_agent(self, email, first_name, last_name, agent_status):
        user = User.objects.create_user(
            email=email,
            password="x",
            first_name=first_name,
            last_name=last_name,
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=agent_status,
        )
        return user

    def _qs(self):
        return ProjectPermission.objects.filter(project=self.project)

    def test_filter_status_empty_returns_queryset(self):
        filtered = AllAgentsFilter().filter_status(self._qs(), "status", [])
        self.assertEqual(filtered.count(), 3)

    def test_filter_status_online_excludes_paused_agents(self):
        filtered = AllAgentsFilter().filter_status(
            self._qs(), "status", ["online"]
        )

        self.assertIn(self.online_perm, filtered)
        self.assertNotIn(self.paused_perm, filtered)
        self.assertNotIn(self.offline_perm, filtered)

    def test_filter_status_offline(self):
        filtered = AllAgentsFilter().filter_status(
            self._qs(), "status", ["offline"]
        )

        self.assertIn(self.offline_perm, filtered)
        self.assertNotIn(self.online_perm, filtered)

    def test_filter_status_custom_pause_name(self):
        filtered = AllAgentsFilter().filter_status(
            self._qs(), "status", ["Lunch"]
        )

        self.assertIn(self.paused_perm, filtered)
        self.assertNotIn(self.online_perm, filtered)

    def test_filter_agent_by_email_fragment(self):
        filtered = AllAgentsFilter().filter_agent(
            self._qs(), "agent", ["online@"]
        )

        self.assertIn(self.online_perm, filtered)
        self.assertNotIn(self.offline_perm, filtered)

    def test_filter_agent_empty_returns_queryset(self):
        filtered = AllAgentsFilter().filter_agent(self._qs(), "agent", [])
        self.assertEqual(filtered.count(), 3)

    def test_filter_name_by_full_name_fragment(self):
        filtered = AllAgentsFilter().filter_name(self._qs(), "name", ["Ana"])

        self.assertIn(self.online_perm, filtered)
        self.assertNotIn(self.offline_perm, filtered)

    def test_filter_sector(self):
        filtered = AllAgentsFilter().filter_sector(
            self._qs(), "sector", [self.sector.uuid]
        )

        self.assertIn(self.online_perm, filtered)
        self.assertNotIn(self.offline_perm, filtered)

    def test_filter_queue(self):
        filtered = AllAgentsFilter().filter_queue(
            self._qs(), "queue", [self.other_queue.uuid]
        )

        self.assertIn(self.offline_perm, filtered)
        self.assertNotIn(self.online_perm, filtered)

    def test_filter_sector_empty_returns_queryset(self):
        filtered = AllAgentsFilter().filter_sector(self._qs(), "sector", [])
        self.assertEqual(filtered.count(), 3)

    def test_filter_queue_empty_returns_queryset(self):
        filtered = AllAgentsFilter().filter_queue(self._qs(), "queue", [])
        self.assertEqual(filtered.count(), 3)

    def test_filter_status_ignores_blank_values(self):
        filtered = AllAgentsFilter().filter_status(
            self._qs(), "status", ["", None]
        )
        self.assertEqual(filtered.count(), 3)

    def test_filter_name_empty_returns_queryset(self):
        filtered = AllAgentsFilter().filter_name(self._qs(), "name", [])
        self.assertEqual(filtered.count(), 3)

    def test_filter_name_ignores_blank_values(self):
        filtered = AllAgentsFilter().filter_name(self._qs(), "name", ["", None])
        self.assertEqual(filtered.count(), 3)

    def test_filter_agent_ignores_blank_values(self):
        filtered = AllAgentsFilter().filter_agent(self._qs(), "agent", ["", None])
        self.assertEqual(filtered.count(), 3)
