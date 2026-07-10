from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import (
    AgentDisconnectLog,
    AgentStatusLog,
    CustomStatus,
    CustomStatusType,
)
from chats.apps.projects.tasks import create_agent_disconnect_log, log_agent_status_change


User = get_user_model()


class CreateAgentDisconnectLogTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Disconnect Project")
        self.agent = User.objects.create_user(email="agent@example.com", password="x")
        self.admin = User.objects.create_user(email="admin@example.com", password="x")

    def test_creates_log(self):
        create_agent_disconnect_log(
            str(self.project.uuid), self.agent.email, self.admin.email
        )
        self.assertEqual(AgentDisconnectLog.objects.count(), 1)
        log = AgentDisconnectLog.objects.get()
        self.assertEqual(log.agent, self.agent)
        self.assertEqual(log.disconnected_by, self.admin)
        self.assertEqual(log.project, self.project)


@override_settings(USE_TZ=True)
class LogAgentStatusChangeTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Status Project", timezone="UTC")
        self.agent = User.objects.create_user(
            email="status-agent@example.com", password="x"
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

    def test_online_creates_log(self):
        log_agent_status_change(
            self.agent.email, str(self.project.uuid), status="ONLINE"
        )
        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        self.assertEqual(log.status_changes[0]["status"], "ONLINE")

    def test_offline_without_custom_status(self):
        log_agent_status_change(
            self.agent.email, str(self.project.uuid), status="OFFLINE"
        )
        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        self.assertEqual(log.status_changes[0]["status"], "OFFLINE")

    def test_break_with_custom_status_name(self):
        log_agent_status_change(
            self.agent.email,
            str(self.project.uuid),
            status="OFFLINE",
            custom_status_name="Lunch",
        )
        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        self.assertEqual(log.status_changes[0]["status"], "BREAK")
        self.assertEqual(log.status_changes[0]["custom_status"], "Lunch")

    def test_in_service_custom_status(self):
        log_agent_status_change(
            self.agent.email,
            str(self.project.uuid),
            status="OFFLINE",
            custom_status_name="In-Service",
        )
        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        self.assertEqual(log.status_changes[0]["status"], "In-Service")

    def test_skips_duplicate_status(self):
        log_agent_status_change(
            self.agent.email, str(self.project.uuid), status="ONLINE"
        )
        log_agent_status_change(
            self.agent.email, str(self.project.uuid), status="ONLINE"
        )
        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        self.assertEqual(len(log.status_changes), 1)

    def test_appends_different_status(self):
        log_agent_status_change(
            self.agent.email, str(self.project.uuid), status="ONLINE"
        )
        log_agent_status_change(
            self.agent.email, str(self.project.uuid), status="OFFLINE"
        )
        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        self.assertEqual(len(log.status_changes), 2)
        self.assertEqual(log.status_changes[1]["status"], "OFFLINE")

    def test_resolves_active_custom_status(self):
        status_type = CustomStatusType.objects.create(
            project=self.project, name="Coffee"
        )
        CustomStatus.objects.create(
            user=self.agent,
            project=self.project,
            status_type=status_type,
            is_active=True,
        )
        log_agent_status_change(
            self.agent.email, str(self.project.uuid), status="OFFLINE"
        )
        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        self.assertEqual(log.status_changes[0]["custom_status"], "Coffee")
        self.assertEqual(log.status_changes[0]["status"], "BREAK")
