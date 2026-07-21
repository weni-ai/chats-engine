from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.msgs.models import BulkMessageSend, BulkMessageSendStatus
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


class TestBulkSendMessages(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Bulk Project")
        self.other_project = Project.objects.create(name="Other Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue A", sector=self.sector)

        self.admin = User.objects.create_user(
            email="admin@example.com", password="testpass123"
        )
        self.other_admin = User.objects.create_user(
            email="other.admin@example.com", password="testpass123"
        )
        self.attendant = User.objects.create_user(
            email="attendant@example.com", password="testpass123"
        )
        self.agent = User.objects.create_user(
            email="agent@example.com", password="testpass123"
        )

        ProjectPermission.objects.create(
            project=self.project,
            user=self.admin,
            role=ProjectPermission.ROLE_ADMIN,
        )
        ProjectPermission.objects.create(
            project=self.other_project,
            user=self.other_admin,
            role=ProjectPermission.ROLE_ADMIN,
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=self.attendant,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self.url = reverse("message-bulk-send")
        self.project_uuid = str(self.project.uuid)

    def _payload(self, **overrides):
        data = {
            "text": "Bulk hello",
            "status": ["ongoing", "waiting"],
            "project": self.project_uuid,
            "queues": [str(self.queue.uuid)],
            "agents": [self.agent.email],
        }
        data.update(overrides)
        return data

    def _post(self, user, data):
        self.client.force_authenticate(user=user)
        return self.client.post(self.url, data, format="json")

    def test_unauthenticated_is_unauthorized(self):
        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_attendant_is_forbidden(self):
        response = self._post(self.attendant, self._payload())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_of_other_project_is_forbidden(self):
        response = self._post(self.other_admin, self._payload())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_requires_project(self):
        payload = self._payload()
        del payload["project"]

        response = self._post(self.admin, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_status(self):
        payload = self._payload()
        del payload["status"]

        response = self._post(self.admin, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_status_returns_400(self):
        response = self._post(self.admin, self._payload(status=[]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_status_returns_400(self):
        response = self._post(self.admin, self._payload(status=["closed"]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.msgs.usecases.start_bulk_send_messages.process_bulk_message_send.delay")
    def test_admin_can_start_bulk_send(self, mock_delay):
        response = self._post(self.admin, self._payload())

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], "PROCESSING")
        self.assertIn("uuid", response.data)

        bulk_send = BulkMessageSend.objects.get(uuid=response.data["uuid"])
        self.assertEqual(bulk_send.status, BulkMessageSendStatus.PENDING)
        self.assertEqual(bulk_send.user, self.admin)
        self.assertEqual(bulk_send.project, self.project)
        self.assertEqual(bulk_send.text, "Bulk hello")
        self.assertEqual(
            bulk_send.filter_snapshot,
            {
                "statuses": ["ongoing", "waiting"],
                "queues": [str(self.queue.uuid)],
                "agents": [self.agent.email],
            },
        )
        mock_delay.assert_called_once_with(bulk_send.uuid)

    @patch("chats.apps.msgs.usecases.start_bulk_send_messages.process_bulk_message_send.delay")
    def test_empty_queues_and_agents_store_empty_lists(self, mock_delay):
        response = self._post(
            self.admin,
            self._payload(queues=[], agents=[]),
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        bulk_send = BulkMessageSend.objects.get(uuid=response.data["uuid"])
        self.assertEqual(
            bulk_send.filter_snapshot,
            {
                "statuses": ["ongoing", "waiting"],
                "queues": [],
                "agents": [],
            },
        )
        mock_delay.assert_called_once_with(bulk_send.uuid)

    @patch("chats.apps.msgs.usecases.start_bulk_send_messages.process_bulk_message_send.delay")
    def test_null_queues_and_agents_store_empty_lists(self, mock_delay):
        response = self._post(
            self.admin,
            self._payload(queues=None, agents=None),
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        bulk_send = BulkMessageSend.objects.get(uuid=response.data["uuid"])
        self.assertEqual(
            bulk_send.filter_snapshot,
            {
                "statuses": ["ongoing", "waiting"],
                "queues": [],
                "agents": [],
            },
        )
        mock_delay.assert_called_once_with(bulk_send.uuid)
