from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.test import TestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.choices import BulkMessageSendRoomStatus
from chats.apps.msgs.models import BulkMessageSend, BulkMessageSendStatus
from chats.apps.msgs.usecases.get_bulk_send_rooms import GetBulkSendRoomsUseCase
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class GetBulkSendRoomsUseCaseTests(TestCase):
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
        self.waiting_room_queue_one = Room.objects.create(
            contact=Contact.objects.create(name="Contact Waiting"),
            queue=self.queue_one,
            user=None,
            is_active=True,
            is_waiting=False,
        )
        self.flow_start_room = Room.objects.create(
            contact=Contact.objects.create(name="Contact Flow Start"),
            queue=self.queue_one,
            user=None,
            is_active=True,
            is_waiting=True,
        )
        self.inactive_room = Room.objects.create(
            contact=Contact.objects.create(name="Contact Inactive"),
            queue=self.queue_one,
            user=self.agent_one,
            is_active=False,
        )
        self.other_project_room = Room.objects.create(
            contact=Contact.objects.create(name="Contact Other"),
            queue=self.other_queue,
            user=self.agent_one,
            is_active=True,
        )

        self.usecase = GetBulkSendRoomsUseCase()

    def _create_bulk_send(self, queues=None, agents=None, statuses=None):
        if statuses is None:
            statuses = [
                BulkMessageSendRoomStatus.ONGOING,
                BulkMessageSendRoomStatus.WAITING,
            ]
        return BulkMessageSend.objects.create(
            user=self.requester,
            project=self.project,
            text="Bulk hello",
            filter_snapshot={
                "statuses": list(statuses),
                "queues": [str(q) for q in (queues or [])],
                "agents": list(agents or []),
            },
            status=BulkMessageSendStatus.PENDING,
        )

    def test_returns_queryset_not_list(self):
        bulk_send = self._create_bulk_send()

        result = self.usecase.execute(bulk_send)

        self.assertIsInstance(result, QuerySet)
        self.assertNotIsInstance(result, list)

    def test_empty_filters_return_all_active_rooms_in_project(self):
        bulk_send = self._create_bulk_send()

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(
            list(result),
            [
                self.room_queue_one_agent_one,
                self.room_queue_one_agent_two,
                self.room_queue_two_agent_one,
                self.waiting_room_queue_one,
            ],
        )

    def test_filters_by_queues_only(self):
        bulk_send = self._create_bulk_send(queues=[self.queue_one.uuid])

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(
            list(result),
            [
                self.room_queue_one_agent_one,
                self.room_queue_one_agent_two,
                self.waiting_room_queue_one,
            ],
        )

    def test_filters_by_agents_only(self):
        bulk_send = self._create_bulk_send(agents=[self.agent_one.email])

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(
            list(result),
            [self.room_queue_one_agent_one, self.room_queue_two_agent_one],
        )

    def test_filters_by_queues_and_agents_intersection(self):
        bulk_send = self._create_bulk_send(
            queues=[self.queue_one.uuid],
            agents=[self.agent_one.email],
        )

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(list(result), [self.room_queue_one_agent_one])

    def test_filters_by_ongoing_status_only(self):
        bulk_send = self._create_bulk_send(
            statuses=[BulkMessageSendRoomStatus.ONGOING],
        )

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(
            list(result),
            [
                self.room_queue_one_agent_one,
                self.room_queue_one_agent_two,
                self.room_queue_two_agent_one,
            ],
        )
        self.assertNotIn(self.waiting_room_queue_one, list(result))

    def test_filters_by_waiting_status_only(self):
        bulk_send = self._create_bulk_send(
            statuses=[BulkMessageSendRoomStatus.WAITING],
        )

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(list(result), [self.waiting_room_queue_one])

    def test_filters_by_ongoing_and_waiting_statuses(self):
        bulk_send = self._create_bulk_send(
            statuses=[
                BulkMessageSendRoomStatus.ONGOING,
                BulkMessageSendRoomStatus.WAITING,
            ],
        )

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(
            list(result),
            [
                self.room_queue_one_agent_one,
                self.room_queue_one_agent_two,
                self.room_queue_two_agent_one,
                self.waiting_room_queue_one,
            ],
        )

    def test_filters_by_status_and_queues_intersection(self):
        bulk_send = self._create_bulk_send(
            statuses=[BulkMessageSendRoomStatus.WAITING],
            queues=[self.queue_one.uuid],
        )

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(list(result), [self.waiting_room_queue_one])

    def test_filters_by_status_and_agents_intersection(self):
        bulk_send = self._create_bulk_send(
            statuses=[BulkMessageSendRoomStatus.ONGOING],
            agents=[self.agent_one.email],
        )

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(
            list(result),
            [self.room_queue_one_agent_one, self.room_queue_two_agent_one],
        )

    def test_excludes_flow_start_rooms(self):
        bulk_send = self._create_bulk_send()

        result = self.usecase.execute(bulk_send)

        self.assertNotIn(self.flow_start_room, list(result))

    def test_empty_statuses_returns_no_rooms(self):
        bulk_send = self._create_bulk_send(statuses=[])

        result = self.usecase.execute(bulk_send)

        self.assertEqual(list(result), [])

    def test_excludes_inactive_rooms(self):
        bulk_send = self._create_bulk_send(queues=[self.queue_one.uuid])

        result = self.usecase.execute(bulk_send)

        self.assertNotIn(self.inactive_room, list(result))

    def test_excludes_rooms_from_other_projects(self):
        bulk_send = self._create_bulk_send()

        result = self.usecase.execute(bulk_send)

        self.assertNotIn(self.other_project_room, list(result))
