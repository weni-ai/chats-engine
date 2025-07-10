import uuid
from unittest.mock import Mock

from django.test import TestCase
from django.utils import timezone
from rest_framework import status

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.usecases.integrate_ticketers import IntegratedTicketers
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


class TestIntegratedTicketers(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="test@example.com", first_name="Test", last_name="User"
        )

        self.org_uuid = str(uuid.uuid4())

        self.principal_project = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Principal Project",
            org=self.org_uuid,
            config={"its_principal": True},
            timezone="America/Sao_Paulo",
            date_format="D",
        )

        self.secondary_project = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Secondary Project",
            org=self.org_uuid,
            config={"its_principal": False},
            timezone="America/Sao_Paulo",
            date_format="D",
        )

        self.permission = ProjectPermission.objects.create(
            user=self.user,
            project=self.principal_project,
            role=ProjectPermission.ROLE_ADMIN,
        )

        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.principal_project,
            rooms_limit=5,
            work_start=timezone.now().time(),
            work_end=timezone.now().time(),
            config={"secondary_project": str(self.secondary_project.uuid)},
        )

        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

        self.integration = IntegratedTicketers()
        self.mock_flows_client = Mock()
        self.integration.flows_client = self.mock_flows_client

    def test_check_ticketer_exists_when_not_integrated(self):
        result = self.integration._check_ticketer_exists(str(self.sector.uuid))
        self.assertFalse(result)

    def test_check_ticketer_exists_when_integrated(self):
        self.sector.config = self.sector.config or {}
        self.sector.config["ticketer_integrated"] = True
        self.sector.save()

        result = self.integration._check_ticketer_exists(str(self.sector.uuid))
        self.assertTrue(result)

    def test_check_queue_exists_when_not_integrated(self):
        result = self.integration._check_queue_exists(str(self.queue.uuid))
        self.assertFalse(result)

    def test_check_queue_exists_when_integrated(self):
        self.queue.config = self.queue.config or {}
        self.queue.config["queue_integrated"] = True
        self.queue.save()

        result = self.integration._check_queue_exists(str(self.queue.uuid))
        self.assertTrue(result)

    def test_mark_ticketer_integrated(self):
        self.integration._mark_ticketer_integrated(str(self.sector.uuid))

        self.sector.refresh_from_db()
        self.assertTrue(self.sector.config.get("ticketer_integrated", False))

    def test_mark_queue_integrated(self):
        self.integration._mark_queue_integrated(str(self.queue.uuid))

        self.queue.refresh_from_db()
        self.assertTrue(self.queue.config.get("queue_integrated", False))

    def test_integrate_ticketer_success(self):
        mock_response = Mock()
        mock_response.status_code = status.HTTP_201_CREATED
        self.mock_flows_client.create_ticketer.return_value = mock_response

        result = self.integration.integrate_ticketer(self.principal_project)

        self.assertEqual(result["integrated"], 1)
        self.assertEqual(result["skipped"], 0)

        self.sector.refresh_from_db()
        self.assertTrue(self.sector.config.get("ticketer_integrated", False))
        self.mock_flows_client.create_ticketer.assert_called_once()

    def test_integrate_ticketer_already_integrated(self):
        self.sector.config = self.sector.config or {}
        self.sector.config["ticketer_integrated"] = True
        self.sector.save()

        result = self.integration.integrate_ticketer(self.principal_project)

        self.assertEqual(result["integrated"], 0)
        self.assertEqual(result["skipped"], 1)
        self.mock_flows_client.create_ticketer.assert_not_called()

    def test_integrate_ticketer_flows_error(self):
        mock_response = Mock()
        mock_response.status_code = status.HTTP_400_BAD_REQUEST
        mock_response.content = b"Error message"
        self.mock_flows_client.create_ticketer.return_value = mock_response

        with self.assertRaises(Exception):
            self.integration.integrate_ticketer(self.principal_project)

        self.sector.refresh_from_db()
        self.assertFalse(self.sector.config.get("ticketer_integrated", False))

    def test_integrate_topic_success(self):
        mock_response = Mock()
        mock_response.status_code = status.HTTP_201_CREATED
        self.mock_flows_client.create_queue.return_value = mock_response

        result = self.integration.integrate_topic(self.principal_project)

        self.assertEqual(result["integrated"], 1)
        self.assertEqual(result["skipped"], 0)

        self.queue.refresh_from_db()
        self.assertTrue(self.queue.config.get("queue_integrated", False))
        self.mock_flows_client.create_queue.assert_called_once()

    def test_integrate_topic_already_integrated(self):
        self.queue.config = self.queue.config or {}
        self.queue.config["queue_integrated"] = True
        self.queue.save()

        result = self.integration.integrate_topic(self.principal_project)

        self.assertEqual(result["integrated"], 0)
        self.assertEqual(result["skipped"], 1)
        self.mock_flows_client.create_queue.assert_not_called()

    def test_integrate_individual_ticketer_success(self):
        mock_response = Mock()
        mock_response.status_code = status.HTTP_201_CREATED
        self.mock_flows_client.create_ticketer.return_value = mock_response

        result = self.integration.integrate_individual_ticketer(
            self.principal_project, str(self.secondary_project.uuid)
        )

        self.assertEqual(result["status"], "success")

        self.sector.refresh_from_db()
        self.assertTrue(self.sector.config.get("ticketer_integrated", False))
        self.mock_flows_client.create_ticketer.assert_called_once()

    def test_integrate_individual_ticketer_already_integrated(self):
        self.sector.config = self.sector.config or {}
        self.sector.config["ticketer_integrated"] = True
        self.sector.save()

        result = self.integration.integrate_individual_ticketer(
            self.principal_project, str(self.secondary_project.uuid)
        )

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "already_integrated")
        self.mock_flows_client.create_ticketer.assert_not_called()

    def test_integrate_individual_ticketer_multiple_sectors_error(self):
        Sector.objects.create(
            name="Another Sector",
            project=self.principal_project,
            rooms_limit=5,
            work_start=timezone.now().time(),
            work_end=timezone.now().time(),
            config={"secondary_project": str(self.secondary_project.uuid)},
        )

        with self.assertRaises(Exception):
            self.integration.integrate_individual_ticketer(
                self.principal_project, str(self.secondary_project.uuid)
            )

    def test_integrate_individual_topic_success(self):
        mock_response = Mock()
        mock_response.status_code = status.HTTP_201_CREATED
        self.mock_flows_client.create_queue.return_value = mock_response

        result = self.integration.integrate_individual_topic(
            self.principal_project, str(self.secondary_project.uuid)
        )

        self.assertEqual(result["integrated"], 1)
        self.assertEqual(result["skipped"], 0)

        self.queue.refresh_from_db()
        self.assertTrue(self.queue.config.get("queue_integrated", False))
        self.mock_flows_client.create_queue.assert_called_once()

    def test_integrate_individual_topic_already_integrated(self):
        self.queue.config = self.queue.config or {}
        self.queue.config["queue_integrated"] = True
        self.queue.save()

        result = self.integration.integrate_individual_topic(
            self.principal_project, str(self.secondary_project.uuid)
        )

        self.assertEqual(result["integrated"], 0)
        self.assertEqual(result["skipped"], 1)
        self.mock_flows_client.create_queue.assert_not_called()

    def test_integrate_ticketer_with_multiple_secondary_projects(self):
        another_secondary = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Another Secondary",
            org=self.org_uuid,
            config={"its_principal": False},
            timezone="America/Sao_Paulo",
            date_format="D",
        )

        another_sector = Sector.objects.create(
            name="Another Sector",
            project=self.principal_project,
            rooms_limit=5,
            work_start=timezone.now().time(),
            work_end=timezone.now().time(),
            config={"secondary_project": str(another_secondary.uuid)},
        )

        mock_response = Mock()
        mock_response.status_code = status.HTTP_201_CREATED
        self.mock_flows_client.create_ticketer.return_value = mock_response

        result = self.integration.integrate_ticketer(self.principal_project)

        self.assertEqual(result["integrated"], 2)
        self.assertEqual(result["skipped"], 0)

        self.sector.refresh_from_db()
        another_sector.refresh_from_db()
        self.assertTrue(self.sector.config.get("ticketer_integrated", False))
        self.assertTrue(another_sector.config.get("ticketer_integrated", False))
        self.assertEqual(self.mock_flows_client.create_ticketer.call_count, 2)

    def test_integrate_topic_with_multiple_queues(self):
        another_queue = Queue.objects.create(name="Another Queue", sector=self.sector)

        mock_response = Mock()
        mock_response.status_code = status.HTTP_201_CREATED
        self.mock_flows_client.create_queue.return_value = mock_response

        result = self.integration.integrate_topic(self.principal_project)

        self.assertEqual(result["integrated"], 2)
        self.assertEqual(result["skipped"], 0)

        self.queue.refresh_from_db()
        another_queue.refresh_from_db()
        self.assertTrue(self.queue.config.get("queue_integrated", False))
        self.assertTrue(another_queue.config.get("queue_integrated", False))
        self.assertEqual(self.mock_flows_client.create_queue.call_count, 2)

    def test_integration_with_nonexistent_sector(self):
        nonexistent_uuid = str(uuid.uuid4())
        result = self.integration._check_ticketer_exists(nonexistent_uuid)
        self.assertFalse(result)

    def test_integration_with_nonexistent_queue(self):
        nonexistent_uuid = str(uuid.uuid4())
        result = self.integration._check_queue_exists(nonexistent_uuid)
        self.assertFalse(result)

    def test_mark_integration_with_nonexistent_sector(self):
        nonexistent_uuid = str(uuid.uuid4())
        self.integration._mark_ticketer_integrated(nonexistent_uuid)

    def test_mark_integration_with_nonexistent_queue(self):
        nonexistent_uuid = str(uuid.uuid4())
        self.integration._mark_queue_integrated(nonexistent_uuid)

    def test_integration_with_empty_config(self):
        self.sector.config = {}
        self.sector.save()

        result = self.integration._check_ticketer_exists(str(self.sector.uuid))
        self.assertFalse(result)

        self.integration._mark_ticketer_integrated(str(self.sector.uuid))

        self.sector.refresh_from_db()
        self.assertTrue(self.sector.config.get("ticketer_integrated", False))

    def test_integration_with_none_config(self):
        self.sector.config = None
        self.sector.save()

        result = self.integration._check_ticketer_exists(str(self.sector.uuid))
        self.assertFalse(result)

        self.integration._mark_ticketer_integrated(str(self.sector.uuid))

        self.sector.refresh_from_db()
        self.assertTrue(self.sector.config.get("ticketer_integrated", False))
