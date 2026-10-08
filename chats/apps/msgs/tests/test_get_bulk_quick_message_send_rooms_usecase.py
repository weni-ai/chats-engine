from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.test import TestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import BulkQuickMessageSend, BulkQuickMessageSendStatus
from chats.apps.msgs.usecases.get_bulk_quick_message_send_rooms import (
    GetBulkQuickMessageSendRoomsUseCase,
)
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class GetBulkQuickMessageSendRoomsUseCaseTests(TestCase):
    def setUp(self):
        self.attendant = User.objects.create_user(
            email="attendant@test.com",
            password="testpass123",
            first_name="Attendant",
            last_name="User",
        )
        self.other_agent = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
            first_name="Other",
            last_name="Agent",
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

        self.contact_one = Contact.objects.create(name="Contact 1")
        self.contact_two = Contact.objects.create(name="Contact 2")
        self.contact_three = Contact.objects.create(name="Contact 3")

        self.room_contact_one = Room.objects.create(
            contact=self.contact_one,
            queue=self.queue_one,
            user=self.attendant,
            is_active=True,
        )
        self.room_contact_two = Room.objects.create(
            contact=self.contact_two,
            queue=self.queue_two,
            user=self.attendant,
            is_active=True,
        )
        self.room_other_agent = Room.objects.create(
            contact=self.contact_three,
            queue=self.queue_one,
            user=self.other_agent,
            is_active=True,
        )
        self.waiting_room = Room.objects.create(
            contact=Contact.objects.create(name="Contact Waiting"),
            queue=self.queue_one,
            user=None,
            is_active=True,
            is_waiting=False,
        )
        self.flow_start_room = Room.objects.create(
            contact=Contact.objects.create(name="Contact Flow Start"),
            queue=self.queue_one,
            user=self.attendant,
            is_active=True,
            is_waiting=True,
        )
        self.inactive_room = Room.objects.create(
            contact=Contact.objects.create(name="Contact Inactive"),
            queue=self.queue_one,
            user=self.attendant,
            is_active=False,
        )
        self.other_project_room = Room.objects.create(
            contact=Contact.objects.create(name="Contact Other"),
            queue=self.other_queue,
            user=self.attendant,
            is_active=True,
        )

        self.usecase = GetBulkQuickMessageSendRoomsUseCase()

    def _create_bulk_send(self, contacts=None):
        return BulkQuickMessageSend.objects.create(
            user=self.attendant,
            project=self.project,
            text="Quick hello",
            contacts=contacts,
            status=BulkQuickMessageSendStatus.PENDING,
        )

    def test_returns_queryset_not_list(self):
        bulk_send = self._create_bulk_send(contacts=None)

        result = self.usecase.execute(bulk_send)

        self.assertIsInstance(result, QuerySet)
        self.assertNotIsInstance(result, list)

    def test_null_contacts_return_all_ongoing_rooms_of_attendant(self):
        bulk_send = self._create_bulk_send(contacts=None)

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(
            list(result),
            [self.room_contact_one, self.room_contact_two],
        )

    def test_filters_by_contact_uuids(self):
        bulk_send = self._create_bulk_send(
            contacts=[str(self.contact_one.uuid)],
        )

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(list(result), [self.room_contact_one])

    def test_filters_by_multiple_contact_uuids(self):
        bulk_send = self._create_bulk_send(
            contacts=[str(self.contact_one.uuid), str(self.contact_two.uuid)],
        )

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(
            list(result),
            [self.room_contact_one, self.room_contact_two],
        )

    def test_contact_filter_excludes_other_agent_rooms(self):
        bulk_send = self._create_bulk_send(
            contacts=[str(self.contact_one.uuid), str(self.contact_three.uuid)],
        )

        result = self.usecase.execute(bulk_send)

        self.assertCountEqual(list(result), [self.room_contact_one])
        self.assertNotIn(self.room_other_agent, list(result))

    def test_empty_contacts_return_no_rooms(self):
        bulk_send = self._create_bulk_send(contacts=[])

        result = self.usecase.execute(bulk_send)

        self.assertEqual(list(result), [])

    def test_excludes_other_agent_rooms(self):
        bulk_send = self._create_bulk_send(contacts=None)

        result = self.usecase.execute(bulk_send)

        self.assertNotIn(self.room_other_agent, list(result))

    def test_excludes_waiting_rooms(self):
        bulk_send = self._create_bulk_send(contacts=None)

        result = self.usecase.execute(bulk_send)

        self.assertNotIn(self.waiting_room, list(result))

    def test_excludes_flow_start_rooms(self):
        bulk_send = self._create_bulk_send(contacts=None)

        result = self.usecase.execute(bulk_send)

        self.assertNotIn(self.flow_start_room, list(result))

    def test_excludes_inactive_rooms(self):
        bulk_send = self._create_bulk_send(contacts=None)

        result = self.usecase.execute(bulk_send)

        self.assertNotIn(self.inactive_room, list(result))

    def test_excludes_rooms_from_other_projects(self):
        bulk_send = self._create_bulk_send(contacts=None)

        result = self.usecase.execute(bulk_send)

        self.assertNotIn(self.other_project_room, list(result))

    def test_excludes_rooms_from_soft_deleted_queue(self):
        self.queue_one.is_deleted = True
        self.queue_one.save(update_fields=["is_deleted"])

        bulk_send = self._create_bulk_send(contacts=None)

        result = list(self.usecase.execute(bulk_send))

        self.assertNotIn(self.room_contact_one, result)
        self.assertCountEqual(result, [self.room_contact_two])

    def test_excludes_rooms_from_soft_deleted_sector(self):
        self.sector.is_deleted = True
        self.sector.save(update_fields=["is_deleted"])

        bulk_send = self._create_bulk_send(contacts=None)

        result = list(self.usecase.execute(bulk_send))

        self.assertEqual(result, [])
