from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import AgentDisconnectLog, AgentStatusLog
from chats.apps.projects.tasks import (
    create_agent_disconnect_log,
    log_agent_status_change,
)


class _BaseProjectTaskTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Task Project")
        self.agent = User.objects.create(email="agent@test.com")
        self.disconnector = User.objects.create(email="manager@test.com")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )


class TestCreateAgentDisconnectLog(_BaseProjectTaskTestCase):
    def test_creates_log_entry(self):
        create_agent_disconnect_log.run(
            project_uuid=str(self.project.uuid),
            agent_email=self.agent.email,
            disconnected_by_email=self.disconnector.email,
        )

        log = AgentDisconnectLog.objects.get()
        self.assertEqual(log.project, self.project)
        self.assertEqual(log.agent, self.agent)
        self.assertEqual(log.disconnected_by, self.disconnector)


class TestLogAgentStatusChange(_BaseProjectTaskTestCase):
    def _last_change(self, log):
        return log.status_changes[-1]

    def test_creates_initial_online_entry(self):
        log_agent_status_change.run(
            agent_email=self.agent.email,
            project_uuid=str(self.project.uuid),
            status="ONLINE",
        )

        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        self.assertEqual(len(log.status_changes), 1)
        entry = self._last_change(log)
        self.assertEqual(entry["status"], "ONLINE")
        self.assertIn("timestamp", entry)
        self.assertNotIn("custom_status", entry)

    def test_creates_offline_entry_when_no_custom_status(self):
        log_agent_status_change.run(
            agent_email=self.agent.email,
            project_uuid=str(self.project.uuid),
            status="OFFLINE",
        )

        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        entry = self._last_change(log)
        self.assertEqual(entry["status"], "OFFLINE")

    def test_creates_in_service_custom_entry(self):
        log_agent_status_change.run(
            agent_email=self.agent.email,
            project_uuid=str(self.project.uuid),
            status="OFFLINE",
            custom_status_name="In-Service",
            custom_status_type_uuid="11111111-1111-1111-1111-111111111111",
        )

        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        entry = self._last_change(log)
        self.assertEqual(entry["status"], "In-Service")
        self.assertEqual(entry["custom_status"], "In-Service")

    def test_creates_break_custom_entry_for_other_status(self):
        log_agent_status_change.run(
            agent_email=self.agent.email,
            project_uuid=str(self.project.uuid),
            status="OFFLINE",
            custom_status_name="Lunch",
            custom_status_type_uuid="22222222-2222-2222-2222-222222222222",
        )

        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        entry = self._last_change(log)
        self.assertEqual(entry["status"], "BREAK")
        self.assertEqual(entry["custom_status"], "Lunch")

    def test_appends_new_entry_to_existing_log(self):
        log_agent_status_change.run(
            agent_email=self.agent.email,
            project_uuid=str(self.project.uuid),
            status="ONLINE",
        )
        log_agent_status_change.run(
            agent_email=self.agent.email,
            project_uuid=str(self.project.uuid),
            status="OFFLINE",
        )

        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        self.assertEqual(len(log.status_changes), 2)
        self.assertEqual(log.status_changes[0]["status"], "ONLINE")
        self.assertEqual(log.status_changes[1]["status"], "OFFLINE")

    def test_dedup_when_appending_same_status(self):
        log_agent_status_change.run(
            agent_email=self.agent.email,
            project_uuid=str(self.project.uuid),
            status="ONLINE",
        )
        log_agent_status_change.run(
            agent_email=self.agent.email,
            project_uuid=str(self.project.uuid),
            status="ONLINE",
        )

        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        self.assertEqual(len(log.status_changes), 1)

    @patch("chats.apps.projects.tasks.logger.error")
    def test_logs_error_and_reraises_on_failure(self, mock_log_error):
        with self.assertRaises(Exception):
            log_agent_status_change.run(
                agent_email="missing@test.com",
                project_uuid=str(self.project.uuid),
                status="ONLINE",
            )

        mock_log_error.assert_called()

    @patch(
        "chats.apps.projects.models.models.CustomStatus.objects.filter"
    )
    def test_infers_custom_status_from_active_status(self, mock_filter):
        active = type(
            "FakeStatus",
            (),
            {
                "status_type": type(
                    "T",
                    (),
                    {
                        "name": "In-Service",
                        "uuid": "33333333-3333-3333-3333-333333333333",
                    },
                )()
            },
        )()
        mock_filter.return_value.first.return_value = active

        log_agent_status_change.run(
            agent_email=self.agent.email,
            project_uuid=str(self.project.uuid),
            status="OFFLINE",
        )

        log = AgentStatusLog.objects.get(agent=self.agent, project=self.project)
        entry = self._last_change(log)
        self.assertEqual(entry["status"], "In-Service")
        self.assertEqual(entry["custom_status"], "In-Service")
