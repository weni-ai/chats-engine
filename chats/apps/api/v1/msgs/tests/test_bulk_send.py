from unittest.mock import patch
import uuid

from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.msgs.models import BulkMessageSend, BulkMessageSendStatus
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.projects.tests.decorators import with_project_permission
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


class BaseBulkSendMessagesViewSetTestCase(APITestCase):
    """
    Base test case for bulk send messages views.
    """

    def bulk_send(self, data: dict) -> Response:
        """
        Post to the bulk send messages endpoint.
        """
        url = reverse("message-bulk-send")

        return self.client.post(url, data=data, format="json")

    def bulk_send_payload(self, **overrides) -> dict:
        """
        Build a valid bulk send payload, applying optional overrides.
        """
        data = {
            "text": "Bulk hello",
            "status": ["ongoing", "waiting"],
            "project": str(self.project.uuid),
            "queues": [str(self.queue.uuid)],
            "agents": [self.agent.email],
        }
        data.update(overrides)
        return data


class TestBulkSendMessagesViewSetAsAnonymousUser(BaseBulkSendMessagesViewSetTestCase):
    """
    Test bulk send messages view set as anonymous.
    """

    def setUp(self) -> None:
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue A", sector=self.sector)
        self.agent = User.objects.create_user(email="agent@example.com")

    def test_cannot_bulk_send_as_anonymous(self) -> None:
        """
        Test that anonymous users cannot start a bulk send.
        """
        response = self.bulk_send(self.bulk_send_payload())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestBulkSendMessagesViewSetAsAuthenticatedUser(BaseBulkSendMessagesViewSetTestCase):
    """
    Test bulk send messages view set as authenticated user.
    """

    def setUp(self) -> None:
        self.user = User.objects.create_user(email="testuser@test.com")
        self.agent = User.objects.create_user(email="agent@example.com")
        self.project = Project.objects.create(name="Test Project")
        self.other_project = Project.objects.create(name="Other Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue A", sector=self.sector)

        self.client.force_authenticate(user=self.user)

    def test_cannot_bulk_send_without_project_permission(self) -> None:
        """
        Test that authenticated users without project permission cannot start a bulk send.
        """
        response = self.bulk_send(self.bulk_send_payload())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    def test_cannot_bulk_send_as_attendant(self) -> None:
        """
        Test that attendant users cannot start a bulk send.
        """
        response = self.bulk_send(self.bulk_send_payload())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_bulk_send_as_admin_of_other_project(self) -> None:
        """
        Test that admins of another project cannot start a bulk send.
        """
        ProjectPermission.objects.create(
            project=self.other_project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

        response = self.bulk_send(self.bulk_send_payload())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_bulk_send_without_project(self) -> None:
        """
        Test that the project field is required.
        """
        payload = self.bulk_send_payload()
        del payload["project"]

        response = self.bulk_send(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["project"][0].code, "required")

    @with_project_permission()
    def test_cannot_bulk_send_without_status(self) -> None:
        """
        Test that the status field is required.
        """
        payload = self.bulk_send_payload()
        del payload["status"]

        response = self.bulk_send(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["status"][0].code, "required")

    @with_project_permission()
    def test_cannot_bulk_send_with_empty_status(self) -> None:
        """
        Test that status cannot be an empty list.
        """
        response = self.bulk_send(self.bulk_send_payload(status=[]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @with_project_permission()
    def test_cannot_bulk_send_with_invalid_status(self) -> None:
        """
        Test that status must be a valid room status choice.
        """
        response = self.bulk_send(self.bulk_send_payload(status=["closed"]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @with_project_permission()
    def test_cannot_bulk_send_without_text(self) -> None:
        """
        Test that the text field is required.
        """
        payload = self.bulk_send_payload()
        del payload["text"]

        response = self.bulk_send(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["text"][0].code, "required")

    @with_project_permission()
    @patch(
        "chats.apps.msgs.usecases.start_bulk_send_messages.process_bulk_message_send.delay"
    )
    def test_can_bulk_send_as_admin(self, mock_delay) -> None:
        """
        Test that admin users can start a bulk send.
        """
        response = self.bulk_send(self.bulk_send_payload())

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], "PROCESSING")
        self.assertIn("uuid", response.data)

        bulk_send = BulkMessageSend.objects.get(uuid=response.data["uuid"])
        self.assertEqual(bulk_send.status, BulkMessageSendStatus.PENDING)
        self.assertEqual(bulk_send.user, self.user)
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

    @with_project_permission()
    @patch(
        "chats.apps.msgs.usecases.start_bulk_send_messages.process_bulk_message_send.delay"
    )
    def test_can_bulk_send_with_empty_queues_and_agents(self, mock_delay) -> None:
        """
        Test that empty queues and agents are stored as empty lists.
        """
        response = self.bulk_send(self.bulk_send_payload(queues=[], agents=[]))

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

    @with_project_permission()
    @patch(
        "chats.apps.msgs.usecases.start_bulk_send_messages.process_bulk_message_send.delay"
    )
    def test_can_bulk_send_with_null_queues_and_agents(self, mock_delay) -> None:
        """
        Test that null queues and agents are stored as empty lists.
        """
        response = self.bulk_send(self.bulk_send_payload(queues=None, agents=None))

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

    @with_project_permission()
    def test_cannot_bulk_send_with_nonexistent_project(self) -> None:
        """
        Test that a nonexistent project returns forbidden when the user is not its admin.
        """
        response = self.bulk_send(
            self.bulk_send_payload(project=str(uuid.uuid4()))
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
