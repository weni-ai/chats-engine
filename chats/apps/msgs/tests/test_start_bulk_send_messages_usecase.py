import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.msgs.models import BulkMessageSend, BulkMessageSendStatus, Message
from chats.apps.msgs.usecases.start_bulk_send_messages import StartBulkSendMessagesUseCase
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector

User = get_user_model()


class StartBulkSendMessagesUseCaseTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            email="requester@test.com",
            password="testpass123",
            first_name="Requester",
            last_name="User",
        )
        self.agent_one = User.objects.create_user(
            email="agent1@test.com",
            password="testpass123",
            first_name="Agent",
            last_name="One",
        )

        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue_one = Queue.objects.create(name="Queue One", sector=self.sector)

        self.usecase = StartBulkSendMessagesUseCase()
        self.text = "Bulk hello"

    def test_creates_pending_bulk_message_send_with_filter_snapshot(self):
        queues = [self.queue_one.uuid]
        agents = [self.agent_one.email]

        bulk_send = self.usecase.execute(
            user_email=self.requester.email,
            text=self.text,
            project_uuid=self.project.uuid,
            queues=queues,
            agents=agents,
        )

        self.assertIsInstance(bulk_send, BulkMessageSend)
        self.assertEqual(bulk_send.status, BulkMessageSendStatus.PENDING)
        self.assertEqual(bulk_send.user, self.requester)
        self.assertEqual(bulk_send.project, self.project)
        self.assertEqual(bulk_send.text, self.text)
        self.assertEqual(
            bulk_send.filter_snapshot,
            {
                "queues": [str(self.queue_one.uuid)],
                "agents": [self.agent_one.email],
            },
        )
        self.assertEqual(Message.objects.count(), 0)

    def test_empty_queues_and_agents_store_empty_filter_snapshot(self):
        bulk_send = self.usecase.execute(
            user_email=self.requester.email,
            text=self.text,
            project_uuid=self.project.uuid,
            queues=None,
            agents=[],
        )

        self.assertEqual(bulk_send.filter_snapshot, {"queues": [], "agents": []})
        self.assertEqual(bulk_send.status, BulkMessageSendStatus.PENDING)

    def test_raises_when_user_email_does_not_exist(self):
        with self.assertRaises(User.DoesNotExist):
            self.usecase.execute(
                user_email="missing@test.com",
                text=self.text,
                project_uuid=self.project.uuid,
            )

    def test_raises_when_project_uuid_does_not_exist(self):
        with self.assertRaises(Project.DoesNotExist):
            self.usecase.execute(
                user_email=self.requester.email,
                text=self.text,
                project_uuid=uuid.uuid4(),
            )
