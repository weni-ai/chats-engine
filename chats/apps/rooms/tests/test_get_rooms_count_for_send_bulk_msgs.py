from datetime import time

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.rooms.usecases.get_rooms_count_for_send_bulk_msgs import (
    GetRoomsCountForSendBulkMsgsUseCase,
)
from chats.apps.sectors.models import Sector


class GetRoomsCountForSendBulkMsgsUseCaseTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Bulk Project")
        self.other_project = Project.objects.create(name="Other Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.other_project,
            rooms_limit=10,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue A", sector=self.sector)
        self.queue_b = Queue.objects.create(name="Queue B", sector=self.sector)
        self.other_queue = Queue.objects.create(
            name="Other Queue", sector=self.other_sector
        )

        self.agent = User.objects.create(email="agent@example.com")
        self.agent_b = User.objects.create(email="agent.b@example.com")

        self.usecase = GetRoomsCountForSendBulkMsgsUseCase()
        self.project_uuid = str(self.project.uuid)

    def _create_room(self, *, queue=None, user=None, is_active=True, contact_name="C"):
        contact = Contact.objects.create(name=contact_name)
        return Room.objects.create(
            queue=queue or self.queue,
            contact=contact,
            user=user,
            is_active=is_active,
            project_uuid=self.project_uuid
            if (queue or self.queue).sector.project_id == self.project.pk
            else str(self.other_project.uuid),
        )

    def test_counts_waiting_rooms(self):
        self._create_room(user=None)
        self._create_room(user=self.agent, contact_name="Ongoing")

        count = self.usecase.execute(
            project_uuid=self.project_uuid,
            statuses=["waiting"],
        )

        self.assertEqual(count, 1)

    def test_counts_ongoing_rooms(self):
        self._create_room(user=None)
        self._create_room(user=self.agent, contact_name="Ongoing")

        count = self.usecase.execute(
            project_uuid=self.project_uuid,
            statuses=["ongoing"],
        )

        self.assertEqual(count, 1)

    def test_counts_waiting_and_ongoing(self):
        self._create_room(user=None)
        self._create_room(user=self.agent, contact_name="Ongoing")
        self._create_room(user=None, is_active=False, contact_name="Closed")

        count = self.usecase.execute(
            project_uuid=self.project_uuid,
            statuses=["waiting", "ongoing"],
        )

        self.assertEqual(count, 2)

    def test_filters_by_queues(self):
        self._create_room(queue=self.queue, user=None)
        self._create_room(queue=self.queue_b, user=None, contact_name="Other queue")

        count = self.usecase.execute(
            project_uuid=self.project_uuid,
            statuses=["waiting"],
            queues=[self.queue.uuid],
        )

        self.assertEqual(count, 1)

    def test_empty_queues_means_all_queues(self):
        self._create_room(queue=self.queue, user=None)
        self._create_room(queue=self.queue_b, user=None, contact_name="Other queue")

        count = self.usecase.execute(
            project_uuid=self.project_uuid,
            statuses=["waiting"],
            queues=[],
        )

        self.assertEqual(count, 2)

    def test_filters_by_agents(self):
        self._create_room(user=self.agent)
        self._create_room(user=self.agent_b, contact_name="Other agent")

        count = self.usecase.execute(
            project_uuid=self.project_uuid,
            statuses=["ongoing"],
            agents=[self.agent.email],
        )

        self.assertEqual(count, 1)

    def test_empty_agents_means_all_agents(self):
        self._create_room(user=self.agent)
        self._create_room(user=self.agent_b, contact_name="Other agent")

        count = self.usecase.execute(
            project_uuid=self.project_uuid,
            statuses=["ongoing"],
            agents=[],
        )

        self.assertEqual(count, 2)

    def test_scopes_to_project(self):
        self._create_room(user=None)
        Room.objects.create(
            queue=self.other_queue,
            contact=Contact.objects.create(name="Other project"),
            is_active=True,
            project_uuid=str(self.other_project.uuid),
        )

        count = self.usecase.execute(
            project_uuid=self.project_uuid,
            statuses=["waiting"],
        )

        self.assertEqual(count, 1)
