from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch
import uuid

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.api.v1.msgs.serializers import BulkSendRecentHistorySerializer
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import (
    BulkMessageSend,
    BulkMessageSendMessage,
    BulkMessageSendMessageStatus,
    BulkMessageSendStatus,
)
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.projects.tests.decorators import with_project_permission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
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


class TestBulkSendMessagesViewSetAsAuthenticatedUser(
    BaseBulkSendMessagesViewSetTestCase
):
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
        response = self.bulk_send(self.bulk_send_payload(project=str(uuid.uuid4())))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class BaseBulkSendHasPastMessagesViewSetTestCase(APITestCase):
    """
    Base test case for bulk send has-past-messages views.
    """

    def has_past_messages(self, project: str = None) -> Response:
        """
        Get the bulk send has-past-messages endpoint.
        """
        url = reverse("message-bulk-send-has-past-messages")
        params = {}
        if project is not None:
            params["project"] = project

        return self.client.get(url, data=params)


class TestBulkSendHasPastMessagesViewSetAsAnonymousUser(
    BaseBulkSendHasPastMessagesViewSetTestCase
):
    """
    Test bulk send has-past-messages view set as anonymous.
    """

    def setUp(self) -> None:
        self.project = Project.objects.create(name="Test Project")

    def test_cannot_has_past_messages_as_anonymous(self) -> None:
        """
        Test that anonymous users cannot check past bulk send messages.
        """
        response = self.has_past_messages(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestBulkSendHasPastMessagesViewSetAsAuthenticatedUser(
    BaseBulkSendHasPastMessagesViewSetTestCase
):
    """
    Test bulk send has-past-messages view set as authenticated user.
    """

    def setUp(self) -> None:
        self.user = User.objects.create_user(email="testuser@test.com")
        self.project = Project.objects.create(name="Test Project")
        self.other_project = Project.objects.create(name="Other Project")

        self.client.force_authenticate(user=self.user)

    def test_cannot_has_past_messages_without_project_permission(self) -> None:
        """
        Test that authenticated users without project permission cannot check.
        """
        response = self.has_past_messages(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    def test_cannot_has_past_messages_as_attendant(self) -> None:
        """
        Test that attendant users cannot check past bulk send messages.
        """
        response = self.has_past_messages(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_has_past_messages_as_admin_of_other_project(self) -> None:
        """
        Test that admins of another project cannot check past bulk send messages.
        """
        ProjectPermission.objects.create(
            project=self.other_project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

        response = self.has_past_messages(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_has_past_messages_without_project(self) -> None:
        """
        Test that the project query param is required.
        """
        response = self.has_past_messages()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["project"][0].code, "required")

    @with_project_permission()
    def test_returns_false_when_no_bulk_send_exists(self) -> None:
        """
        Test that status is false when the project has no bulk send history.
        """
        response = self.has_past_messages(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], False)

    @with_project_permission()
    def test_returns_true_when_bulk_send_exists(self) -> None:
        """
        Test that status is true when the project has bulk send history.
        """
        BulkMessageSend.objects.create(
            user=self.user,
            project=self.project,
            text="Past bulk message",
        )

        response = self.has_past_messages(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], True)

    @with_project_permission()
    @override_settings(BULK_SEND_HAS_PAST_MESSAGES_CACHE_TTL=123)
    @patch("chats.apps.api.v1.msgs.viewsets.cache.set")
    @patch("chats.apps.api.v1.msgs.viewsets.cache.get", return_value=None)
    def test_caches_true_response_with_settings_ttl(
        self, mock_cache_get, mock_cache_set
    ) -> None:
        """
        Test that a true response is cached using the configured TTL.
        """
        BulkMessageSend.objects.create(
            user=self.user,
            project=self.project,
            text="Past bulk message",
        )

        response = self.has_past_messages(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], True)
        mock_cache_set.assert_called_once_with(
            f"bulk_send:has_past_messages:{self.project.uuid}",
            True,
            123,
        )

    @with_project_permission()
    @patch("chats.apps.api.v1.msgs.viewsets.cache.set")
    @patch("chats.apps.api.v1.msgs.viewsets.cache.get", return_value=None)
    def test_does_not_cache_false_response(
        self, mock_cache_get, mock_cache_set
    ) -> None:
        """
        Test that a false response is not cached.
        """
        response = self.has_past_messages(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], False)
        mock_cache_set.assert_not_called()

    @with_project_permission()
    @patch("chats.apps.api.v1.msgs.viewsets.cache.get", return_value=True)
    @patch("chats.apps.api.v1.msgs.viewsets.cache.set")
    def test_returns_true_from_cache_without_db_lookup(
        self, mock_cache_set, mock_cache_get
    ) -> None:
        """
        Test that a cache hit returns true without querying the database.
        """
        response = self.has_past_messages(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], True)
        mock_cache_set.assert_not_called()


class BaseBulkSendRecentHistoryViewSetTestCase(APITestCase):
    """
    Base test case for bulk send recent-history views.
    """

    def recent_history(self, project: str = None) -> Response:
        """
        Get the bulk send recent-history endpoint.
        """
        url = reverse("message-bulk-send-recent-history")
        params = {}
        if project is not None:
            params["project"] = project

        return self.client.get(url, data=params)


class TestBulkSendRecentHistoryViewSetAsAnonymousUser(
    BaseBulkSendRecentHistoryViewSetTestCase
):
    """
    Test bulk send recent-history view set as anonymous.
    """

    def setUp(self) -> None:
        self.project = Project.objects.create(name="Test Project")

    def test_cannot_recent_history_as_anonymous(self) -> None:
        """
        Test that anonymous users cannot fetch recent bulk send history.
        """
        response = self.recent_history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestBulkSendRecentHistoryViewSetAsAuthenticatedUser(
    BaseBulkSendRecentHistoryViewSetTestCase
):
    """
    Test bulk send recent-history view set as authenticated user.
    """

    def setUp(self) -> None:
        self.user = User.objects.create_user(email="testuser@test.com")
        self.project = Project.objects.create(name="Test Project")
        self.other_project = Project.objects.create(name="Other Project")

        self.client.force_authenticate(user=self.user)

    def test_cannot_recent_history_without_project_permission(self) -> None:
        """
        Test that authenticated users without project permission cannot fetch.
        """
        response = self.recent_history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    def test_cannot_recent_history_as_attendant(self) -> None:
        """
        Test that attendant users cannot fetch recent bulk send history.
        """
        response = self.recent_history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_recent_history_as_admin_of_other_project(self) -> None:
        """
        Test that admins of another project cannot fetch recent bulk send history.
        """
        ProjectPermission.objects.create(
            project=self.other_project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

        response = self.recent_history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_recent_history_without_project(self) -> None:
        """
        Test that the project query param is required.
        """
        response = self.recent_history()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["project"][0].code, "required")

    @with_project_permission()
    def test_returns_empty_results_when_no_bulk_send_exists(self) -> None:
        """
        Test that results is empty when the project has no recent bulk send history.
        """
        response = self.recent_history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    @with_project_permission()
    def test_returns_recent_bulk_send(self) -> None:
        """
        Test that recent bulk sends are returned with uuid, text, and sent_at.
        """
        bulk_send = BulkMessageSend.objects.create(
            user=self.user,
            project=self.project,
            text="Recent bulk message",
        )

        response = self.recent_history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["uuid"], str(bulk_send.uuid))
        self.assertEqual(response.data["results"][0]["text"], "Recent bulk message")
        self.assertEqual(
            response.data["results"][0]["sent_at"],
            BulkSendRecentHistorySerializer(bulk_send).data["sent_at"],
        )

    @with_project_permission()
    def test_excludes_bulk_send_older_than_window(self) -> None:
        """
        Test that bulk sends older than the recent window are excluded.
        """
        bulk_send = BulkMessageSend.objects.create(
            user=self.user,
            project=self.project,
            text="Old bulk message",
        )
        BulkMessageSend.objects.filter(uuid=bulk_send.uuid).update(
            created_on=timezone.now() - timedelta(minutes=61)
        )

        response = self.recent_history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    @with_project_permission()
    def test_excludes_bulk_send_from_other_project(self) -> None:
        """
        Test that bulk sends from another project are excluded.
        """
        BulkMessageSend.objects.create(
            user=self.user,
            project=self.other_project,
            text="Other project bulk message",
        )

        response = self.recent_history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    @with_project_permission()
    @override_settings(BULK_SEND_RECENT_HISTORY_WINDOW_MINUTES=30)
    def test_window_is_settings_driven(self) -> None:
        """
        Test that the recent history window uses the configured setting.
        """
        bulk_send = BulkMessageSend.objects.create(
            user=self.user,
            project=self.project,
            text="Borderline bulk message",
        )
        BulkMessageSend.objects.filter(uuid=bulk_send.uuid).update(
            created_on=timezone.now() - timedelta(minutes=31)
        )

        response = self.recent_history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    @with_project_permission()
    @patch("chats.apps.api.v1.msgs.viewsets.logger.info")
    def test_limits_results_to_100_and_logs_when_exceeded(
        self, mock_logger_info
    ) -> None:
        """
        Test that only the last 100 records are returned and excess is logged.
        """
        BulkMessageSend.objects.bulk_create(
            [
                BulkMessageSend(
                    user=self.user,
                    project=self.project,
                    text=f"Bulk message {i}",
                )
                for i in range(101)
            ]
        )

        response = self.recent_history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 100)
        mock_logger_info.assert_called_once()


class BaseBulkSendHistoryViewSetTestCase(APITestCase):
    """
    Base test case for bulk send history views.
    """

    def history(self, **params) -> Response:
        """
        Get the bulk send history endpoint.
        """
        url = reverse("message-bulk-send-history")
        return self.client.get(url, data=params)

    def _create_sector_and_queue(self, project: Project, queue_name: str = "Queue"):
        sector = Sector.objects.create(
            name="Sector",
            project=project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        queue = Queue.objects.create(name=queue_name, sector=sector)
        return sector, queue

    def _create_bulk_message(
        self,
        *,
        user: User,
        project: Project,
        queue: Queue,
        contact_name: str,
        status_value: str = BulkMessageSendMessageStatus.SUCCESS,
        created_on=None,
    ) -> BulkMessageSendMessage:
        bulk_send = BulkMessageSend.objects.create(
            user=user,
            project=project,
            text="Bulk hello",
            status=BulkMessageSendStatus.FINISHED,
        )
        room = Room.objects.create(
            contact=Contact.objects.create(name=contact_name),
            queue=queue,
        )
        bulk_message = BulkMessageSendMessage.objects.create(
            bulk_message_send=bulk_send,
            room=room,
            status=status_value,
        )
        if created_on is not None:
            BulkMessageSendMessage.objects.filter(uuid=bulk_message.uuid).update(
                created_on=created_on
            )
            bulk_message.refresh_from_db()
        return bulk_message


class TestBulkSendHistoryViewSetAsAnonymousUser(BaseBulkSendHistoryViewSetTestCase):
    """
    Test bulk send history view set as anonymous.
    """

    def setUp(self) -> None:
        self.project = Project.objects.create(name="Test Project")

    def test_cannot_history_as_anonymous(self) -> None:
        """
        Test that anonymous users cannot fetch bulk send history.
        """
        response = self.history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestBulkSendHistoryViewSetAsAuthenticatedUser(BaseBulkSendHistoryViewSetTestCase):
    """
    Test bulk send history view set as authenticated user.
    """

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="moderator@test.com",
            first_name="Kallil",
        )
        self.other_user = User.objects.create_user(
            email="other@test.com",
            first_name="Other",
        )
        self.project = Project.objects.create(name="Test Project")
        self.other_project = Project.objects.create(name="Other Project")
        self.sector, self.queue = self._create_sector_and_queue(
            self.project, queue_name="Pokedex"
        )
        self.other_sector, self.other_queue = self._create_sector_and_queue(
            self.other_project, queue_name="Other Queue"
        )

        self.client.force_authenticate(user=self.user)

    def test_cannot_history_without_project_permission(self) -> None:
        """
        Test that authenticated users without project permission cannot fetch.
        """
        response = self.history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    def test_cannot_history_as_attendant(self) -> None:
        """
        Test that attendant users cannot fetch bulk send history.
        """
        response = self.history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_history_as_admin_of_other_project(self) -> None:
        """
        Test that admins of another project cannot fetch bulk send history.
        """
        ProjectPermission.objects.create(
            project=self.other_project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

        response = self.history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_history_without_project(self) -> None:
        """
        Test that the project query param is required.
        """
        response = self.history()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["project"][0].code, "required")

    @with_project_permission()
    def test_returns_empty_results_when_no_history_exists(self) -> None:
        """
        Test that results is empty when the project has no bulk send history.
        """
        response = self.history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])
        self.assertIsNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    @with_project_permission()
    def test_returns_history_item_shape(self) -> None:
        """
        Test that history items return contact, queue, sent_by, date, and status.
        """
        bulk_message = self._create_bulk_message(
            user=self.user,
            project=self.project,
            queue=self.queue,
            contact_name="Eduardo",
            status_value=BulkMessageSendMessageStatus.FAILED,
        )

        response = self.history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0],
            {
                "contact": {"name": "Eduardo"},
                "queue": {"name": "Pokedex"},
                "sent_by": {"name": "Kallil"},
                "date": bulk_message.created_on.date().isoformat(),
                "status": BulkMessageSendMessageStatus.FAILED,
            },
        )

    @with_project_permission()
    def test_filters_by_date(self) -> None:
        """
        Test that the date filter returns only matching rows.
        """
        matching = self._create_bulk_message(
            user=self.user,
            project=self.project,
            queue=self.queue,
            contact_name="Matching",
            created_on=datetime(2026, 9, 1, 12, 0, tzinfo=dt_timezone.utc),
        )
        self._create_bulk_message(
            user=self.user,
            project=self.project,
            queue=self.queue,
            contact_name="Other Day",
            created_on=datetime(2026, 9, 2, 12, 0, tzinfo=dt_timezone.utc),
        )

        response = self.history(project=str(self.project.uuid), date="2026-09-01")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["contact"]["name"], "Matching")
        self.assertEqual(
            response.data["results"][0]["date"],
            matching.created_on.date().isoformat(),
        )

    @with_project_permission()
    def test_filters_by_sender(self) -> None:
        """
        Test that the sender filter returns only rows from that moderator.
        """
        self._create_bulk_message(
            user=self.user,
            project=self.project,
            queue=self.queue,
            contact_name="From Moderator",
        )
        self._create_bulk_message(
            user=self.other_user,
            project=self.project,
            queue=self.queue,
            contact_name="From Other",
        )

        response = self.history(
            project=str(self.project.uuid),
            sender=self.user.email,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["contact"]["name"], "From Moderator"
        )
        self.assertEqual(response.data["results"][0]["sent_by"]["name"], "Kallil")

    @with_project_permission()
    def test_filters_by_status(self) -> None:
        """
        Test that the status filter returns only matching rows.
        """
        self._create_bulk_message(
            user=self.user,
            project=self.project,
            queue=self.queue,
            contact_name="Success Contact",
            status_value=BulkMessageSendMessageStatus.SUCCESS,
        )
        self._create_bulk_message(
            user=self.user,
            project=self.project,
            queue=self.queue,
            contact_name="Failed Contact",
            status_value=BulkMessageSendMessageStatus.FAILED,
        )

        response = self.history(
            project=str(self.project.uuid),
            status=BulkMessageSendMessageStatus.FAILED,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["contact"]["name"], "Failed Contact"
        )
        self.assertEqual(
            response.data["results"][0]["status"],
            BulkMessageSendMessageStatus.FAILED,
        )

    @with_project_permission()
    def test_filters_by_combined_params(self) -> None:
        """
        Test that date, sender, and status filters can be combined.
        """
        self._create_bulk_message(
            user=self.user,
            project=self.project,
            queue=self.queue,
            contact_name="Match",
            status_value=BulkMessageSendMessageStatus.SUCCESS,
            created_on=datetime(2026, 9, 1, 10, 0, tzinfo=dt_timezone.utc),
        )
        self._create_bulk_message(
            user=self.user,
            project=self.project,
            queue=self.queue,
            contact_name="Wrong Status",
            status_value=BulkMessageSendMessageStatus.FAILED,
            created_on=datetime(2026, 9, 1, 11, 0, tzinfo=dt_timezone.utc),
        )
        self._create_bulk_message(
            user=self.other_user,
            project=self.project,
            queue=self.queue,
            contact_name="Wrong Sender",
            status_value=BulkMessageSendMessageStatus.SUCCESS,
            created_on=datetime(2026, 9, 1, 12, 0, tzinfo=dt_timezone.utc),
        )

        response = self.history(
            project=str(self.project.uuid),
            date="2026-09-01",
            sender=self.user.email,
            status=BulkMessageSendMessageStatus.SUCCESS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["contact"]["name"], "Match")

    @with_project_permission()
    def test_excludes_history_from_other_project(self) -> None:
        """
        Test that history rows from another project are excluded.
        """
        self._create_bulk_message(
            user=self.user,
            project=self.other_project,
            queue=self.other_queue,
            contact_name="Other Project Contact",
        )

        response = self.history(project=str(self.project.uuid))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    @with_project_permission()
    def test_rejects_invalid_status(self) -> None:
        """
        Test that an invalid status query param returns 400.
        """
        response = self.history(
            project=str(self.project.uuid),
            status="PENDING",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @with_project_permission()
    def test_paginates_with_limit_and_offset(self) -> None:
        """
        Test that LimitOffset pagination returns count, next, and pages.
        """
        for i in range(3):
            self._create_bulk_message(
                user=self.user,
                project=self.project,
                queue=self.queue,
                contact_name=f"Contact {i}",
            )

        first_page = self.history(
            project=str(self.project.uuid),
            limit=1,
            offset=0,
        )

        self.assertEqual(first_page.status_code, status.HTTP_200_OK)
        self.assertEqual(first_page.data["count"], 3)
        self.assertEqual(len(first_page.data["results"]), 1)
        self.assertIsNotNone(first_page.data["next"])
        self.assertIsNone(first_page.data["previous"])

        second_page = self.history(
            project=str(self.project.uuid),
            limit=1,
            offset=1,
        )

        self.assertEqual(second_page.status_code, status.HTTP_200_OK)
        self.assertEqual(second_page.data["count"], 3)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertIsNotNone(second_page.data["next"])
        self.assertIsNotNone(second_page.data["previous"])
        self.assertNotEqual(
            first_page.data["results"][0]["contact"]["name"],
            second_page.data["results"][0]["contact"]["name"],
        )
