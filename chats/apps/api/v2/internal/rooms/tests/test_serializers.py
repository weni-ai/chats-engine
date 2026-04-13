from django.test import TestCase
from django.utils import timezone as django_timezone

from chats.apps.accounts.models import User
from chats.apps.api.v2.internal.rooms.serializers import RoomInternalListSerializerV2
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class RoomInternalListSerializerV2Tests(TestCase):
    """Tests for ``RoomInternalListSerializerV2`` (agent, sector, queue shapes)."""

    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(
            name="Serializer Test Project",
            timezone=str(django_timezone.get_current_timezone()),
        )
        cls.sector = Sector.objects.create(
            name="Alpha Sector",
            project=cls.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
            is_deleted=False,
        )
        cls.queue = Queue.objects.create(
            name="Alpha Queue",
            sector=cls.sector,
            is_deleted=False,
        )
        cls.contact = Contact.objects.create(name="Client", email="client@test.com")
        cls.agent = User.objects.create_user(
            email="agent@test.com",
            password="secret",
            first_name="Jane",
            last_name="Doe",
        )

    def _serialize(self, room: Room) -> dict:
        return RoomInternalListSerializerV2(room).data

    def test_agent_is_none_when_room_has_no_user(self):
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=None,
        )
        data = self._serialize(room)
        self.assertIsNone(data["agent"])

    def test_sector_and_queue_are_objects_with_name_and_is_deleted(self):
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
        )
        data = self._serialize(room)
        self.assertEqual(
            data["sector"],
            {"name": "Alpha Sector", "is_deleted": False},
        )
        self.assertEqual(
            data["queue"],
            {"name": "Alpha Queue", "is_deleted": False},
        )

    def test_sector_and_queue_reflect_is_deleted_flags(self):
        self.sector.is_deleted = True
        self.sector.save(update_fields=["is_deleted"])
        self.queue.is_deleted = True
        self.queue.save(update_fields=["is_deleted"])

        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
        )
        data = self._serialize(room)
        self.assertEqual(
            data["sector"],
            {"name": "Alpha Sector", "is_deleted": True},
        )
        self.assertEqual(
            data["queue"],
            {"name": "Alpha Queue", "is_deleted": True},
        )

    def test_sector_and_queue_are_none_when_room_has_no_queue(self):
        room = Room.objects.create(
            contact=self.contact,
            queue=None,
            user=self.agent,
        )
        data = self._serialize(room)
        self.assertIsNone(data["sector"])
        self.assertIsNone(data["queue"])

    def test_agent_includes_name_and_email(self):
        ProjectPermission.objects.create(
            user=self.agent,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
        )
        data = self._serialize(room)
        self.assertEqual(data["agent"]["name"], "Jane Doe")
        self.assertEqual(data["agent"]["email"], "agent@test.com")

    def test_agent_is_deleted_true_when_project_permission_missing(self):
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
        )
        data = self._serialize(room)
        self.assertTrue(data["agent"]["is_deleted"])

    def test_agent_is_deleted_false_when_project_permission_active(self):
        ProjectPermission.objects.create(
            user=self.agent,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
        )
        data = self._serialize(room)
        self.assertFalse(data["agent"]["is_deleted"])

    def test_agent_is_deleted_true_when_project_permission_soft_deleted(self):
        ProjectPermission.all_objects.create(
            user=self.agent,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
            is_deleted=True,
        )
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
        )
        data = self._serialize(room)
        self.assertTrue(data["agent"]["is_deleted"])
