from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
import pytz

from chats.apps.accounts.models import User
from chats.apps.projects.models import (
    Project,
    ProjectPermission,
    CustomStatusType,
    CustomStatus,
)
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector

from chats.apps.api.v1.internal.dashboard.repository import AgentRepository
from chats.apps.api.v1.internal.dashboard.dto import Filters


class TestAgentRepository(TestCase):
    def setUp(self):
        self.repository = AgentRepository()

        self.project = Project.objects.create(
            name="Test Project",
            timezone=pytz.timezone("America/Sao_Paulo"),
            date_format=Project.DATE_FORMAT_DAY_FIRST,
            config={"agents_can_see_queue_history": True, "routing_option": None},
        )

        self.agent1 = User.objects.create(
            email="agent1@test.com", first_name="Agent", last_name="One", is_active=True
        )
        self.agent2 = User.objects.create(
            email="agent2@test.com", first_name="Agent", last_name="Two", is_active=True
        )

        self.permission1 = ProjectPermission.objects.create(
            user=self.agent1,
            project=self.project,
            status="ONLINE",
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.permission2 = ProjectPermission.objects.create(
            user=self.agent2,
            project=self.project,
            status="OFFLINE",
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
            can_trigger_flows=False,
            sign_messages=False,
            open_offline=True,
            can_edit_custom_fields=False,
        )

        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
            default_message="Welcome to the queue",
        )

        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=self.permission1,
            role=QueueAuthorization.ROLE_AGENT,
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=self.permission2,
            role=QueueAuthorization.ROLE_AGENT,
        )

        self.status_type = CustomStatusType.objects.create(
            name="Lunch", project=self.project
        )

        self.custom_status = CustomStatus.objects.create(
            user=self.agent1,
            status_type=self.status_type,
            break_time=30,
            is_active=True,
        )

    def test_get_agents_custom_status_basic(self):
        """Testa a busca básica de agentes com custom status"""
        filters = Filters(
            queue=None,
            sector=None,
            tag=None,
            start_date=None,
            end_date=None,
            agent=None,
            is_weni_admin=False,
        )

        result = self.repository.get_agents_custom_status_and_rooms(
            filters, self.project
        )
        agents = list(result)

        self.assertEqual(len(agents), 2)

        agent1_data = next(a for a in agents if a["email"] == "agent1@test.com")
        self.assertEqual(agent1_data["status"], "ONLINE")
        self.assertTrue(agent1_data["custom_status"])
        self.assertEqual(agent1_data["custom_status"][0]["status_type"], "Lunch")
        self.assertEqual(agent1_data["custom_status"][0]["break_time"], 30)

    def test_get_agents_custom_status_with_filters(self):
        """Testa a busca de agentes com filtros específicos"""
        filters = Filters(
            queue=self.queue,
            sector=None,
            tag=None,
            start_date=None,
            end_date=None,
            agent=self.agent1.email,
            is_weni_admin=False,
        )

        result = self.repository.get_agents_custom_status_and_rooms(
            filters, self.project
        )
        agents = list(result)

        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["email"], self.agent1.email)

    def test_get_agents_custom_status_with_date_range(self):
        """Testa a busca de agentes com filtro de data"""
        now = timezone.now()
        filters = Filters(
            queue=None,
            sector=None,
            tag=None,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
            agent=None,
            is_weni_admin=False,
        )

        result = self.repository.get_agents_custom_status_and_rooms(
            filters, self.project
        )
        agents = list(result)

        self.assertTrue(len(agents) > 0)

    def test_get_agents_custom_status_weni_admin(self):
        """Testa o filtro de admin Weni"""

        weni_agent = User.objects.create(
            email="agent@weni.ai", first_name="Weni", last_name="Agent", is_active=True
        )
        ProjectPermission.objects.create(
            user=weni_agent, project=self.project, status="ONLINE"
        )

        filters = Filters(
            queue=None,
            sector=None,
            tag=None,
            start_date=None,
            end_date=None,
            agent=None,
            is_weni_admin=False,
        )

        result = self.repository.get_agents_custom_status_and_rooms(
            filters, self.project
        )
        agents = list(result)

        self.assertFalse(any(a["email"].endswith("weni.ai") for a in agents))

        filters.is_weni_admin = True
        result = self.repository.get_agents_custom_status_and_rooms(
            filters, self.project
        )
        agents = list(result)

        self.assertTrue(any(a["email"].endswith("weni.ai") for a in agents))

    def test_get_agents_custom_status_inactive_agents(self):
        """Testa que agentes inativos não são retornados"""
        self.agent1.is_active = False
        self.agent1.save()

        filters = Filters(
            queue=None,
            sector=None,
            tag=None,
            start_date=None,
            end_date=None,
            agent=None,
            is_weni_admin=False,
        )

        result = self.repository.get_agents_custom_status_and_rooms(
            filters, self.project
        )
        agents = list(result)

        self.assertFalse(any(a["email"] == self.agent1.email for a in agents))
