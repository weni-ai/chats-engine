from datetime import time
from unittest.mock import PropertyMock, patch

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.msgs.exceptions import MessageCreateError
from chats.apps.msgs.models import Message
from chats.apps.msgs.usecases.create_agent_message import (
    CreateAgentMessageUseCase,
    PostCreateAgentMessageUseCase,
)
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class TestCreateAgentMessageUseCase(TestCase):
    def setUp(self):
        self.use_case = CreateAgentMessageUseCase()
        self.user = User.objects.create_user(
            email="agent@example.com",
            password="testpass123",
            first_name="Maria",
            last_name="Silva",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(9, 0),
            work_end=time(18, 0),
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            name="Contact", email="contact@example.com"
        )
        self.room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            is_active=True,
        )
        ProjectPermission.objects.create(
            user=self.user,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
            last_seen=timezone.now(),
        )

    @patch(
        "chats.apps.msgs.usecases.create_agent_message.calculate_first_response_time_task.delay"
    )
    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_execute_success(self, mock_notify_room, mock_first_response_task):
        message = self.use_case.execute(
            self.user,
            {"room": str(self.room.uuid), "text": "Hello"},
        )

        self.assertEqual(message.text, "Hello")
        self.assertEqual(message.user, self.user)
        self.assertEqual(message.room, self.room)
        mock_notify_room.assert_called_once_with("create", True)

        self.room.refresh_from_db()
        self.assertEqual(self.room.last_message, message)

    def test_execute_room_not_found(self):
        with self.assertRaises(MessageCreateError) as ctx:
            self.use_case.execute(
                self.user,
                {"room": "00000000-0000-0000-0000-000000000000", "text": "Hello"},
            )

        self.assertEqual(ctx.exception.error_code, "room_not_found")

    def test_execute_permission_denied(self):
        self.room.user = self.other_user
        self.room.save(update_fields=["user"])

        with self.assertRaises(MessageCreateError) as ctx:
            self.use_case.execute(
                self.user,
                {"room": str(self.room.uuid), "text": "Hello"},
            )

        self.assertEqual(ctx.exception.error_code, "permission_denied")

    def test_execute_room_closed(self):
        self.room.is_active = False
        self.room.save(update_fields=["is_active"])

        with self.assertRaises(MessageCreateError) as ctx:
            self.use_case.execute(
                self.user,
                {"room": str(self.room.uuid), "text": "Hello"},
            )

        self.assertEqual(ctx.exception.error_code, "room_closed")

    @patch("chats.apps.rooms.models.Room.is_24h_valid", new_callable=PropertyMock)
    def test_execute_message_window_expired(self, mock_is_24h_valid):
        mock_is_24h_valid.return_value = False

        with self.assertRaises(MessageCreateError) as ctx:
            self.use_case.execute(
                self.user,
                {"room": str(self.room.uuid), "text": "Hello"},
            )

        self.assertEqual(ctx.exception.error_code, "message_window_expired")

    def test_execute_room_waiting(self):
        self.room.is_waiting = True
        self.room.save(update_fields=["is_waiting"])

        with self.assertRaises(MessageCreateError) as ctx:
            self.use_case.execute(
                self.user,
                {"room": str(self.room.uuid), "text": "Hello"},
            )

        self.assertEqual(ctx.exception.error_code, "room_waiting")

    @patch("django.db.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("chats.apps.ai_features.improve_user_message.tasks.register_message_improvement_task.delay")
    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_execute_with_ai_text_improvement(
        self, mock_notify_room, mock_register_task, _mock_on_commit
    ):
        from chats.apps.ai_features.improve_user_message.choices import (
            ImprovedUserMessageStatusChoices,
            ImprovedUserMessageTypeChoices,
        )

        message = self.use_case.execute(
            self.user,
            {
                "room": str(self.room.uuid),
                "text": "Hello",
                "ai_text_improvement": {
                    "type": ImprovedUserMessageTypeChoices.GRAMMAR_AND_SPELLING,
                    "status": ImprovedUserMessageStatusChoices.USED,
                },
            },
        )

        self.assertEqual(message.text, "Hello")
        mock_register_task.assert_called_once()


class TestPostCreateAgentMessageUseCase(TestCase):
    @patch(
        "chats.apps.msgs.usecases.create_agent_message.calculate_first_response_time_task.delay"
    )
    @patch("chats.apps.msgs.models.Message.notify_room")
    def test_execute_schedules_first_response_time_task(
        self, mock_notify_room, mock_first_response_task
    ):
        user = User.objects.create_user(email="agent@example.com", password="pass")
        project = Project.objects.create(name="Test Project")
        sector = Sector.objects.create(
            name="Test Sector",
            project=project,
            rooms_limit=10,
            work_start=time(9, 0),
            work_end=time(18, 0),
        )
        queue = Queue.objects.create(name="Test Queue", sector=sector)
        room = Room.objects.create(
            queue=queue,
            user=user,
            is_active=True,
            first_user_assigned_at=timezone.now(),
        )
        message = Message.objects.create(room=room, user=user, text="Hi")

        PostCreateAgentMessageUseCase().execute(message)

        mock_first_response_task.assert_called_once_with(str(room.uuid))
