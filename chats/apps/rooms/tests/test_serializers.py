import uuid
from django.test import TestCase


from chats.apps.api.v1.rooms.serializers import (
    AddOrRemoveTagFromRoomSerializer,
    AddRoomTagSerializer,
)
from chats.apps.rooms.models import Room
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
