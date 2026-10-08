from unittest.mock import patch
import uuid

from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.msgs.models import BulkQuickMessageSend, BulkQuickMessageSendStatus
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.projects.tests.decorators import with_project_permission
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


class BaseBulkSendQuickMessageViewSetTestCase(APITestCase):
    """
    Base test case for bulk send quick message views.
    """

    def bulk_send_quick_message(self, data: dict) -> Response:
        """
        Post to the bulk send quick message endpoint.
        """
        url = reverse("message-bulk-send-quick-message")

        return self.client.post(url, data=data, format="json")

    def bulk_send_quick_message_payload(self, **overrides) -> dict:
        """
        Build a valid bulk send quick message payload, applying optional overrides.
        """
        data = {
            "text": "Quick hello",
            "project": str(self.project.uuid),
            "contacts": [str(self.contact_one), str(self.contact_two)],
        }
        data.update(overrides)
        return data


class TestBulkSendQuickMessageViewSetAsAnonymousUser(
    BaseBulkSendQuickMessageViewSetTestCase
):
    """
    Test bulk send quick message view set as anonymous.
    """

    def setUp(self) -> None:
        self.project = Project.objects.create(name="Test Project")
        self.contact_one = uuid.uuid4()
        self.contact_two = uuid.uuid4()

    def test_cannot_bulk_send_quick_message_as_anonymous(self) -> None:
        """
        Test that anonymous users cannot start a bulk quick message send.
        """
        response = self.bulk_send_quick_message(self.bulk_send_quick_message_payload())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestBulkSendQuickMessageViewSetAsAuthenticatedUser(
    BaseBulkSendQuickMessageViewSetTestCase
):
    """
    Test bulk send quick message view set as authenticated user.
    """

    def setUp(self) -> None:
        self.user = User.objects.create_user(email="testuser@test.com")
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
        self.contact_one = uuid.uuid4()
        self.contact_two = uuid.uuid4()

        self.client.force_authenticate(user=self.user)

    def test_cannot_bulk_send_quick_message_without_project_permission(self) -> None:
        """
        Test that authenticated users without project permission cannot start a
        bulk quick message send.
        """
        response = self.bulk_send_quick_message(self.bulk_send_quick_message_payload())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_bulk_send_quick_message_as_attendant_of_other_project(
        self,
    ) -> None:
        """
        Test that attendants of another project cannot start a bulk quick message send.
        """
        ProjectPermission.objects.create(
            project=self.other_project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        response = self.bulk_send_quick_message(self.bulk_send_quick_message_payload())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_bulk_send_quick_message_without_project(self) -> None:
        """
        Test that the project field is required.
        """
        payload = self.bulk_send_quick_message_payload()
        del payload["project"]

        response = self.bulk_send_quick_message(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["project"][0].code, "required")

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    def test_cannot_bulk_send_quick_message_without_text(self) -> None:
        """
        Test that the text field is required.
        """
        payload = self.bulk_send_quick_message_payload()
        del payload["text"]

        response = self.bulk_send_quick_message(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["text"][0].code, "required")

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    def test_cannot_bulk_send_quick_message_with_blank_text(self) -> None:
        """
        Test that the text field cannot be blank.
        """
        response = self.bulk_send_quick_message(
            self.bulk_send_quick_message_payload(text="")
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    def test_cannot_bulk_send_quick_message_with_nonexistent_project(self) -> None:
        """
        Test that a nonexistent project returns forbidden when the user has no
        permission on it.
        """
        response = self.bulk_send_quick_message(
            self.bulk_send_quick_message_payload(project=str(uuid.uuid4()))
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    @patch(
        "chats.apps.msgs.usecases.start_bulk_send_quick_message.process_bulk_quick_message_send.delay"
    )
    def test_can_bulk_send_quick_message_as_attendant_with_contacts(
        self, mock_delay
    ) -> None:
        """
        Test that attendant users can start a bulk quick message send with contacts.
        """
        response = self.bulk_send_quick_message(self.bulk_send_quick_message_payload())

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], "PROCESSING")
        self.assertIn("uuid", response.data)

        bulk_send = BulkQuickMessageSend.objects.get(uuid=response.data["uuid"])
        self.assertEqual(bulk_send.status, BulkQuickMessageSendStatus.PENDING)
        self.assertEqual(bulk_send.user, self.user)
        self.assertEqual(bulk_send.project, self.project)
        self.assertEqual(bulk_send.text, "Quick hello")
        self.assertEqual(
            bulk_send.contacts,
            [str(self.contact_one), str(self.contact_two)],
        )
        mock_delay.assert_called_once_with(bulk_send.uuid)

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    @patch(
        "chats.apps.msgs.usecases.start_bulk_send_quick_message.process_bulk_quick_message_send.delay"
    )
    def test_can_bulk_send_quick_message_with_null_contacts(self, mock_delay) -> None:
        """
        Test that null contacts are stored as null (all ongoing rooms).
        """
        response = self.bulk_send_quick_message(
            self.bulk_send_quick_message_payload(contacts=None)
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        bulk_send = BulkQuickMessageSend.objects.get(uuid=response.data["uuid"])
        self.assertIsNone(bulk_send.contacts)
        mock_delay.assert_called_once_with(bulk_send.uuid)

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    @patch(
        "chats.apps.msgs.usecases.start_bulk_send_quick_message.process_bulk_quick_message_send.delay"
    )
    def test_can_bulk_send_quick_message_with_omitted_contacts(
        self, mock_delay
    ) -> None:
        """
        Test that omitted contacts are treated as null (all ongoing rooms).
        """
        payload = self.bulk_send_quick_message_payload()
        del payload["contacts"]

        response = self.bulk_send_quick_message(payload)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        bulk_send = BulkQuickMessageSend.objects.get(uuid=response.data["uuid"])
        self.assertIsNone(bulk_send.contacts)
        mock_delay.assert_called_once_with(bulk_send.uuid)

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    @patch(
        "chats.apps.msgs.usecases.start_bulk_send_quick_message.process_bulk_quick_message_send.delay"
    )
    def test_can_bulk_send_quick_message_with_empty_contacts(self, mock_delay) -> None:
        """
        Test that empty contacts are stored as an empty list.
        """
        response = self.bulk_send_quick_message(
            self.bulk_send_quick_message_payload(contacts=[])
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        bulk_send = BulkQuickMessageSend.objects.get(uuid=response.data["uuid"])
        self.assertEqual(bulk_send.contacts, [])
        mock_delay.assert_called_once_with(bulk_send.uuid)

    @with_project_permission()
    @patch(
        "chats.apps.msgs.usecases.start_bulk_send_quick_message.process_bulk_quick_message_send.delay"
    )
    def test_can_bulk_send_quick_message_as_admin(self, mock_delay) -> None:
        """
        Test that admin users can start a bulk quick message send.
        """
        response = self.bulk_send_quick_message(self.bulk_send_quick_message_payload())

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], "PROCESSING")
        self.assertIn("uuid", response.data)

        bulk_send = BulkQuickMessageSend.objects.get(uuid=response.data["uuid"])
        self.assertEqual(bulk_send.status, BulkQuickMessageSendStatus.PENDING)
        self.assertEqual(bulk_send.user, self.user)
        self.assertEqual(bulk_send.project, self.project)
        mock_delay.assert_called_once_with(bulk_send.uuid)
