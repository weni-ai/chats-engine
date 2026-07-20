import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import BulkMessageSend, BulkMessageSendStatus, Message
from chats.apps.msgs.usecases.bulk_send_messages import BulkSendMessagesUseCase
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class BulkSendMessagesUseCaseTests(TestCase):
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
        self.agent_two = User.objects.create_user(
            email="agent2@test.com",
            password="testpass123",
            first_name="Agent",
            last_name="Two",
        )

        self.project = Project.objects.create(name="Test Project")
        self.other_project = Project.objects.create(name="Other Project")

        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.other_project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )

        self.queue_one = Queue.objects.create(name="Queue One", sector=self.sector)
        self.queue_two = Queue.objects.create(name="Queue Two", sector=self.sector)
        self.other_queue = Queue.objects.create(
            name="Other Queue", sector=self.other_sector
        )

        self.room_queue_one_agent_one = Room.objects.create(
            contact=Contact.objects.create(name="Contact 1"),
            queue=self.queue_one,
            user=self.agent_one,
            is_active=True,
        )
        self.room_queue_one_agent_two = Room.objects.create(
            contact=Contact.objects.create(name="Contact 2"),
            queue=self.queue_one,
            user=self.agent_two,
            is_active=True,
        )
        self.room_queue_two_agent_one = Room.objects.create(
            contact=Contact.objects.create(name="Contact 3"),
            queue=self.queue_two,
            user=self.agent_one,
            is_active=True,
        )
        self.inactive_room = Room.objects.create(
            contact=Contact.objects.create(name="Contact Inactive"),
            queue=self.queue_one,
            user=self.agent_one,
            is_active=False,
        )
        self.other_project_room = Room.objects.create(
            contact=Contact.objects.create(name="Contact Other Project"),
            queue=self.other_queue,
            user=self.agent_one,
            is_active=True,
        )

        self.usecase = BulkSendMessagesUseCase()
        self.text = "Bulk hello"

    def _room_uuids(self, queues=None, agents=None):
        return set(
            self.usecase._get_rooms(
                project=self.project,
                queues=queues,
                agents=agents,
            ).values_list("uuid", flat=True)
        )

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

    def test_get_rooms_filters_by_project_and_active_only(self):
        room_uuids = self._room_uuids()

        self.assertEqual(
            room_uuids,
            {
                self.room_queue_one_agent_one.uuid,
                self.room_queue_one_agent_two.uuid,
                self.room_queue_two_agent_one.uuid,
            },
        )
        self.assertNotIn(self.inactive_room.uuid, room_uuids)
        self.assertNotIn(self.other_project_room.uuid, room_uuids)

    def test_get_rooms_filters_by_queues(self):
        room_uuids = self._room_uuids(queues=[self.queue_one.uuid])

        self.assertEqual(
            room_uuids,
            {
                self.room_queue_one_agent_one.uuid,
                self.room_queue_one_agent_two.uuid,
            },
        )

    def test_get_rooms_filters_by_agents(self):
        room_uuids = self._room_uuids(agents=[self.agent_two.email])

        self.assertEqual(room_uuids, {self.room_queue_one_agent_two.uuid})

    def test_get_rooms_filters_by_queues_and_agents(self):
        room_uuids = self._room_uuids(
            queues=[self.queue_one.uuid],
            agents=[self.agent_one.email],
        )

        self.assertEqual(room_uuids, {self.room_queue_one_agent_one.uuid})

    def test_empty_queues_and_agents_do_not_narrow_filter(self):
        expected = {
            self.room_queue_one_agent_one.uuid,
            self.room_queue_one_agent_two.uuid,
            self.room_queue_two_agent_one.uuid,
        }

        self.assertEqual(self._room_uuids(queues=[], agents=[]), expected)
        self.assertEqual(self._room_uuids(queues=None, agents=None), expected)

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
