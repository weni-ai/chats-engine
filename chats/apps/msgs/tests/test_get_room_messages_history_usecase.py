import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.exceptions import RoomNotFoundError, RoomStillActiveError
from chats.apps.msgs.models import Message
from chats.apps.msgs.usecases.get_room_messages_history import (
    GetRoomMessagesHistoryUseCase,
)
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room, RoomNote
from chats.apps.sectors.models import Sector

User = get_user_model()


class GetRoomMessagesHistoryUseCaseTests(TestCase):
    def setUp(self):
        self.agent = User.objects.create_user(
            email="agent@test.com",
            password="testpass123",
            first_name="Ana",
            last_name="Agent",
        )
        self.contact = Contact.objects.create(name="Customer")
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
            is_active=True,
        )
        self.other_room = Room.objects.create(
            contact=Contact.objects.create(name="Other Customer"),
            queue=self.queue,
            user=self.agent,
            is_active=True,
        )

        self.usecase = GetRoomMessagesHistoryUseCase()

    def close_room(self, room=None):
        target = room or self.room
        Room.objects.filter(pk=target.pk).update(is_active=False)
        target.refresh_from_db()
        return target

    def test_raises_room_not_found_when_uuid_does_not_exist(self):
        self.close_room()
        with self.assertRaises(RoomNotFoundError):
            self.usecase.execute(
                room_uuid=uuid.uuid4(), project=self.project
            )

    def test_raises_room_not_found_when_room_belongs_to_another_project(self):
        other_project = Project.objects.create(name="Other Project")
        self.close_room()
        with self.assertRaises(RoomNotFoundError):
            self.usecase.execute(
                room_uuid=self.room.uuid, project=other_project
            )

    def test_raises_room_still_active_when_room_is_open(self):
        with self.assertRaises(RoomStillActiveError):
            self.usecase.execute(
                room_uuid=self.room.uuid, project=self.project
            )

    def test_returns_only_messages_from_the_given_room(self):
        msg_in_room = Message.objects.create(
            room=self.room, contact=self.contact, text="Hello room"
        )
        Message.objects.create(
            room=self.other_room,
            contact=self.other_room.contact,
            text="From another room",
        )
        self.close_room()

        result = list(
            self.usecase.execute(room_uuid=self.room.uuid, project=self.project)
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].uuid, msg_in_room.uuid)

    def test_excludes_messages_with_internal_note(self):
        regular_msg = Message.objects.create(
            room=self.room, contact=self.contact, text="Visible"
        )
        note_msg = Message.objects.create(room=self.room, user=self.agent, text="")
        RoomNote.objects.create(
            room=self.room,
            user=self.agent,
            text="Internal observation",
            message=note_msg,
        )
        self.close_room()

        result_uuids = [
            m.uuid
            for m in self.usecase.execute(
                room_uuid=self.room.uuid, project=self.project
            )
        ]

        self.assertIn(regular_msg.uuid, result_uuids)
        self.assertNotIn(note_msg.uuid, result_uuids)

    def test_includes_messages_when_room_has_unanchored_notes(self):
        msg = Message.objects.create(
            room=self.room, contact=self.contact, text="Still visible"
        )
        RoomNote.objects.create(
            room=self.room,
            user=self.agent,
            text="Note without anchor",
            message=None,
        )
        self.close_room()

        result_uuids = [
            m.uuid
            for m in self.usecase.execute(
                room_uuid=self.room.uuid, project=self.project
            )
        ]

        self.assertIn(msg.uuid, result_uuids)

    def test_messages_are_ordered_by_created_on_descending(self):
        msg1 = Message.objects.create(
            room=self.room, contact=self.contact, text="first"
        )
        msg2 = Message.objects.create(
            room=self.room, contact=self.contact, text="second"
        )
        msg3 = Message.objects.create(
            room=self.room, contact=self.contact, text="third"
        )
        self.close_room()

        result = list(
            self.usecase.execute(room_uuid=self.room.uuid, project=self.project)
        )

        self.assertEqual(
            [m.uuid for m in result],
            [msg3.uuid, msg2.uuid, msg1.uuid],
        )

    def test_returns_queryset_instance(self):
        from django.db.models.query import QuerySet

        self.close_room()
        result = self.usecase.execute(
            room_uuid=self.room.uuid, project=self.project
        )

        self.assertIsInstance(result, QuerySet)
