import uuid
from django.conf import settings
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext


from chats.apps.api.v1.rooms.serializers import (
    AddOrRemoveTagFromRoomSerializer,
    AddRoomTagSerializer,
    ListRoomSerializer,
    _get_room_inactivity_timeout_time,
)
from chats.apps.contacts.models import Contact
from chats.apps.rooms.models import Room
from chats.apps.sectors.constants import get_default_inactivity_timeout
from chats.apps.sectors.models import SectorTag
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


class TestAddOrRemoveTagFromRoomSerializer(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="test")
        self.sector = Sector.objects.create(
            name="test",
            project=self.project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="test", sector=self.sector)
        self.room = Room.objects.create(queue=self.queue)
        self.sector_tag = SectorTag.objects.create(name="test", sector=self.sector)

    def test_validate_sector_tag(self):
        serializer = AddOrRemoveTagFromRoomSerializer(
            data={"uuid": self.sector_tag.uuid}, context={"room": self.room}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["sector_tag"], self.sector_tag)

    def test_use_tag_from_another_sector(self):
        sector_tag = SectorTag.objects.create(
            sector=Sector.objects.create(
                name="test 2",
                project=self.project,
                rooms_limit=1,
                work_start="09:00",
                work_end="18:00",
            ),
            name="test 2",
        )

        serializer = AddOrRemoveTagFromRoomSerializer(
            data={"uuid": sector_tag.uuid}, context={"room": self.room}
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["uuid"][0].code, "tag_not_found")

    def test_use_tag_that_does_not_exist(self):
        serializer = AddOrRemoveTagFromRoomSerializer(
            data={"uuid": uuid.uuid4()}, context={"room": self.room}
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["uuid"][0].code, "tag_not_found")


class TestAddRoomTagSerializer(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="test")
        self.sector = Sector.objects.create(
            name="test",
            project=self.project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="test", sector=self.sector)
        self.room = Room.objects.create(queue=self.queue)
        self.sector_tag = SectorTag.objects.create(name="test", sector=self.sector)

    def test_validate_when_room_already_has_tag(self):
        self.room.tags.add(self.sector_tag)

        serializer = AddRoomTagSerializer(
            data={"uuid": self.sector_tag.uuid}, context={"room": self.room}
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["uuid"][0].code, "tag_already_exists")

    def test_validate_when_tag_is_not_in_the_room(self):
        serializer = AddRoomTagSerializer(
            data={"uuid": self.sector_tag.uuid}, context={"room": self.room}
        )
        self.assertTrue(serializer.is_valid())


class TestRoomInactivityTimeoutHelper(TestCase):
    """
    The `_get_room_inactivity_timeout_time` helper is shared by
    `RoomSerializer` and `ListRoomSerializer`. Testing it directly covers both.
    """

    def setUp(self):
        self.project = Project.objects.create(name="test")
        self.sector = Sector.objects.create(
            name="test",
            project=self.project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="test", sector=self.sector)
        self.room = Room.objects.create(queue=self.queue)

    def test_falls_back_to_default_when_sector_not_configured(self):
        self.assertIsNone(self.sector.inactivity_timeout)

        result = _get_room_inactivity_timeout_time(self.room)

        self.assertEqual(result, settings.DEFAULT_MESSAGE_TIMEOUT_TIME)

    def test_returns_sector_value_when_configured(self):
        self.sector.inactivity_timeout = {
            "is_message_timeout_enabled": True,
            "message_timeout_text": "warn",
            "message_timeout_time": 1500,
            "is_close_room_enabled": False,
            "close_room_message_text": "",
            "close_room_timeout_time": None,
        }
        self.sector.save()

        self.room.refresh_from_db()
        result = _get_room_inactivity_timeout_time(self.room)

        self.assertEqual(result, 1500)

    def test_falls_back_when_sector_json_lacks_message_timeout_time(self):
        self.sector.inactivity_timeout = {
            "is_message_timeout_enabled": False,
            "message_timeout_text": "",
            "message_timeout_time": None,
            "is_close_room_enabled": False,
            "close_room_message_text": "",
            "close_room_timeout_time": None,
        }
        self.sector.save()

        self.room.refresh_from_db()
        result = _get_room_inactivity_timeout_time(self.room)

        self.assertEqual(result, settings.DEFAULT_MESSAGE_TIMEOUT_TIME)


class TestRoomIsInactiveField(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="test")
        self.sector = Sector.objects.create(
            name="test",
            project=self.project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="test", sector=self.sector)

    def test_new_room_defaults_to_not_inactive(self):
        room = Room.objects.create(queue=self.queue)

        self.assertFalse(room.is_inactive)


class TestListRoomSerializerInactivityFields(TestCase):
    """
    Ensures the inactivity-related fields appear in the list serializer output
    and that adding them does not introduce N+1 queries when the queryset is
    properly `select_related`-ed (matching `RoomViewset.get_queryset`).
    """

    def setUp(self):
        self.project = Project.objects.create(name="test")
        self.sector = Sector.objects.create(
            name="test",
            project=self.project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
            inactivity_timeout={
                "is_message_timeout_enabled": True,
                "message_timeout_text": "warn",
                "message_timeout_time": 720,
                "is_close_room_enabled": False,
                "close_room_message_text": "",
                "close_room_timeout_time": None,
            },
        )
        self.queue = Queue.objects.create(name="test", sector=self.sector)
        self.contact = Contact.objects.create(name="John")

    def test_serializer_returns_is_inactive_and_inactivity_timeout_time(self):
        room = Room.objects.create(queue=self.queue, contact=self.contact)

        data = ListRoomSerializer(room).data

        self.assertIn("is_inactive", data)
        self.assertFalse(data["is_inactive"])
        self.assertEqual(data["inactivity_timeout_time"], 720)

    def test_serializer_returns_default_timeout_when_sector_not_configured(self):
        sector = Sector.objects.create(
            name="other",
            project=self.project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        queue = Queue.objects.create(name="other", sector=sector)
        contact = Contact.objects.create(name="Jane")
        room = Room.objects.create(queue=queue, contact=contact)

        data = ListRoomSerializer(room).data

        self.assertEqual(
            data["inactivity_timeout_time"],
            get_default_inactivity_timeout()["message_timeout_time"],
        )

    def test_inactivity_fields_do_not_cause_n_plus_one(self):
        for i in range(5):
            contact = Contact.objects.create(name=f"contact-{i}")
            Room.objects.create(queue=self.queue, contact=contact)

        rooms_qs = Room.objects.select_related(
            "user", "contact", "queue", "queue__sector"
        ).all()

        with CaptureQueriesContext(connection) as ctx:
            data = ListRoomSerializer(rooms_qs, many=True).data
            self.assertEqual(len(data), 5)
            for room_data in data:
                self.assertIn("inactivity_timeout_time", room_data)
                self.assertIn("is_inactive", room_data)

        # Single SELECT for rooms (with JOINs for sector/queue/contact/user) plus
        # one query per room for the room pin lookup (`get_is_pinned`). The
        # important part is that reading the sector's `inactivity_timeout`
        # adds zero queries on top of the existing select_related JOINs.
        self.assertLessEqual(len(ctx.captured_queries), 1 + 5)
