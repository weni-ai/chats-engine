from datetime import time, timedelta

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room, RoomNote
from chats.apps.rooms.usecases.build_room_export_data import (
    SENDER_TYPE_AGENT,
    SENDER_TYPE_BOT,
    SENDER_TYPE_CONTACT,
    TIMELINE_ITEM_INTERNAL_NOTE,
    TIMELINE_ITEM_MESSAGE,
    TIMELINE_ITEM_TRANSFER_CHIP,
    BuildRoomExportData,
)
from chats.apps.sectors.models import Sector, SectorTag


class BuildRoomExportDataTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            external_id="contact-1",
            name="Test Contact",
            email="contact@example.com",
            phone="+5511999999999",
            custom_fields={"cpf": "000.000.000-00", "tipo": "vip"},
        )
        self.agent = User.objects.create(email="agent@example.com", first_name="Agent")
        self.other_agent = User.objects.create(
            email="other@example.com", first_name="Other"
        )

        self.room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
            protocol="PROTO-1",
            custom_fields={"motivo": "duvida", "prioridade": "alta"},
        )

        Room.objects.filter(pk=self.room.pk).update(
            ended_at=self.room.created_on + timedelta(hours=2),
            is_active=False,
            ended_by=self.agent.email,
        )
        self.room.refresh_from_db()

        self.usecase = BuildRoomExportData()

    def test_room_block_contains_metadata(self):
        tag = SectorTag.objects.create(sector=self.sector, name="urgent")
        self.room.tags.add(tag)

        data = self.usecase.execute(self.room)

        self.assertEqual(data["room"]["uuid"], str(self.room.uuid))
        self.assertEqual(data["room"]["protocol"], "PROTO-1")
        self.assertEqual(data["room"]["started_at"], self.room.created_on)
        self.assertEqual(data["room"]["ended_at"], self.room.ended_at)
        self.assertEqual(data["room"]["ended_by"], self.agent.email)
        self.assertEqual(data["room"]["tags"], ["urgent"])
        self.assertEqual(
            data["room"]["custom_fields"],
            {"motivo": "duvida", "prioridade": "alta"},
        )

    def test_contact_block_returns_drawer_fields(self):
        data = self.usecase.execute(self.room)

        contact = data["contact"]
        self.assertEqual(contact["name"], "Test Contact")
        self.assertEqual(contact["email"], "contact@example.com")
        self.assertEqual(contact["phone"], "+5511999999999")
        self.assertEqual(contact["external_id"], "contact-1")
        self.assertEqual(
            contact["custom_fields"], {"cpf": "000.000.000-00", "tipo": "vip"}
        )

    def test_contact_block_handles_missing_contact(self):
        self.room.contact = None
        self.room.save = lambda *args, **kwargs: None  # bypass closed-room guard
        Room.objects.filter(pk=self.room.pk).update(contact=None)
        self.room.refresh_from_db()

        data = self.usecase.execute(self.room)

        self.assertEqual(
            data["contact"],
            {
                "name": None,
                "email": None,
                "phone": None,
                "external_id": None,
                "custom_fields": {},
            },
        )

    def test_room_block_falls_back_when_custom_fields_is_none(self):
        Room.objects.filter(pk=self.room.pk).update(custom_fields=None)
        self.room.refresh_from_db()

        data = self.usecase.execute(self.room)

        self.assertEqual(data["room"]["custom_fields"], {})

    def test_agents_block_includes_all_participants(self):
        Message.objects.bulk_create(
            [
                Message(room=self.room, user=self.other_agent, text="hi"),
            ]
        )
        Room.objects.filter(pk=self.room.pk).update(
            full_transfer_history=[
                {
                    "action": "transfer",
                    "from": {"type": "queue", "name": "Q"},
                    "to": {
                        "type": "user",
                        "name": "Other",
                        "email": "other@example.com",
                    },
                    "requested_by": {
                        "type": "user",
                        "name": "Agent",
                        "email": "agent@example.com",
                    },
                }
            ]
        )
        self.room.refresh_from_db()

        data = self.usecase.execute(self.room)

        emails = {a["email"] for a in data["agents"]}
        self.assertEqual(emails, {"agent@example.com", "other@example.com"})

        current = [a for a in data["agents"] if a["is_current"]]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["email"], "agent@example.com")

    def test_agents_block_returns_empty_when_no_participants(self):
        self.room.user = None
        Room.objects.filter(pk=self.room.pk).update(user=None)
        self.room.refresh_from_db()

        data = self.usecase.execute(self.room)

        self.assertEqual(data["agents"], [])

    def test_timeline_includes_messages_with_sender_types(self):
        Message.objects.bulk_create(
            [
                Message(room=self.room, contact=self.contact, text="oi"),
                Message(room=self.room, user=self.agent, text="ola"),
                Message(room=self.room, text="bot reply"),
            ]
        )

        data = self.usecase.execute(self.room)

        message_items = [
            item for item in data["timeline"] if item["type"] == TIMELINE_ITEM_MESSAGE
        ]
        sender_types = [item["sender_type"] for item in message_items]
        self.assertIn(SENDER_TYPE_CONTACT, sender_types)
        self.assertIn(SENDER_TYPE_AGENT, sender_types)
        self.assertIn(SENDER_TYPE_BOT, sender_types)

    def test_timeline_filters_out_feedback_messages(self):
        Message.objects.bulk_create(
            [
                Message(room=self.room, contact=self.contact, text="oi"),
                Message(
                    room=self.room,
                    text='{"method": "rt", "content": {}}',
                ),
                Message(
                    room=self.room,
                    text='{"content": {"action": "transfer"}}',
                ),
            ]
        )

        data = self.usecase.execute(self.room)

        texts = [
            item["text"]
            for item in data["timeline"]
            if item["type"] == TIMELINE_ITEM_MESSAGE
        ]
        self.assertEqual(texts, ["oi"])

    def test_timeline_includes_messages_with_medias(self):
        msg = Message(room=self.room, contact=self.contact, text="foto")
        Message.objects.bulk_create([msg])
        MessageMedia.objects.bulk_create(
            [
                MessageMedia(
                    message=msg,
                    content_type="image/jpeg",
                    media_url="https://example.com/img.jpg",
                ),
            ]
        )

        data = self.usecase.execute(self.room)

        message_items = [
            item for item in data["timeline"] if item["type"] == TIMELINE_ITEM_MESSAGE
        ]
        self.assertEqual(len(message_items), 1)
        medias = message_items[0]["medias"]
        self.assertEqual(len(medias), 1)
        self.assertEqual(medias[0]["content_type"], "image/jpeg")
        self.assertEqual(medias[0]["url"], "https://example.com/img.jpg")
        self.assertIsNone(medias[0]["data_uri"])

    def test_timeline_includes_internal_notes(self):
        note = RoomNote.objects.create(
            room=self.room, user=self.agent, text="nota interna"
        )

        data = self.usecase.execute(self.room)

        note_items = [
            item
            for item in data["timeline"]
            if item["type"] == TIMELINE_ITEM_INTERNAL_NOTE
        ]
        self.assertEqual(len(note_items), 1)
        self.assertEqual(note_items[0]["text"], "nota interna")
        self.assertEqual(note_items[0]["sender_name"], "Agent")
        self.assertIsNone(note_items[0]["anchored_message_uuid"])
        self.assertEqual(note_items[0]["created_on"], note.created_on)

    def test_internal_note_anchors_to_message_uuid(self):
        msg = Message(room=self.room, contact=self.contact, text="ola")
        Message.objects.bulk_create([msg])

        RoomNote.objects.create(
            room=self.room, user=self.agent, text="anchored", message=msg
        )

        data = self.usecase.execute(self.room)

        note_item = next(
            item
            for item in data["timeline"]
            if item["type"] == TIMELINE_ITEM_INTERNAL_NOTE
        )
        self.assertEqual(note_item["anchored_message_uuid"], str(msg.uuid))

    def test_timeline_includes_transfer_chips(self):
        history = [
            {
                "action": "pick",
                "from": {"type": "queue", "name": "Default queue"},
                "to": {
                    "type": "user",
                    "name": "Agent",
                    "email": "agent@example.com",
                },
                "requested_by": {
                    "type": "user",
                    "name": "Agent",
                    "email": "agent@example.com",
                },
            },
            {
                "action": "transfer",
                "from": {"type": "user", "name": "Agent"},
                "to": {"type": "user", "name": "Other"},
                "requested_by": {"type": "user", "name": "Agent"},
            },
        ]
        Room.objects.filter(pk=self.room.pk).update(full_transfer_history=history)
        self.room.refresh_from_db()

        data = self.usecase.execute(self.room)

        chips = [
            item
            for item in data["timeline"]
            if item["type"] == TIMELINE_ITEM_TRANSFER_CHIP
        ]
        self.assertEqual(len(chips), 2)
        self.assertEqual(chips[0]["kind"], "pick")
        self.assertEqual(chips[1]["kind"], "transfer")

    def test_transfer_chip_timestamps_lie_between_start_and_end(self):
        history = [
            {"action": "pick", "from": {}, "to": {}, "requested_by": {}},
            {"action": "transfer", "from": {}, "to": {}, "requested_by": {}},
        ]
        Room.objects.filter(pk=self.room.pk).update(full_transfer_history=history)
        self.room.refresh_from_db()

        data = self.usecase.execute(self.room)

        chips = [
            item
            for item in data["timeline"]
            if item["type"] == TIMELINE_ITEM_TRANSFER_CHIP
        ]
        for chip in chips:
            self.assertGreater(chip["created_on"], self.room.created_on)
            self.assertLess(chip["created_on"], self.room.ended_at)

    def test_timeline_is_sorted_by_created_on(self):
        Message.objects.bulk_create(
            [
                Message(room=self.room, contact=self.contact, text="a"),
                Message(room=self.room, user=self.agent, text="b"),
            ]
        )
        RoomNote.objects.create(room=self.room, user=self.agent, text="n")

        data = self.usecase.execute(self.room)

        timestamps = [item["created_on"] for item in data["timeline"]]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_returns_empty_timeline_when_room_has_nothing(self):
        data = self.usecase.execute(self.room)
        self.assertEqual(data["timeline"], [])

    def test_message_sender_name_falls_back_to_email(self):
        no_name_user = User.objects.create(email="noname@example.com", first_name="")
        Message.objects.bulk_create(
            [Message(room=self.room, user=no_name_user, text="hi")]
        )

        data = self.usecase.execute(self.room)

        item = next(
            item for item in data["timeline"] if item["type"] == TIMELINE_ITEM_MESSAGE
        )
        self.assertEqual(item["sender_name"], "noname@example.com")

    def test_chips_use_action_as_kind(self):
        Room.objects.filter(pk=self.room.pk).update(
            full_transfer_history=[{"action": "forward", "from": {}, "to": {}}]
        )
        self.room.refresh_from_db()

        data = self.usecase.execute(self.room)
        chip = next(
            item
            for item in data["timeline"]
            if item["type"] == TIMELINE_ITEM_TRANSFER_CHIP
        )
        self.assertEqual(chip["kind"], "forward")


class BuildRoomExportDataWithoutEndedAtTests(TestCase):
    """Ensures chip timestamp distribution works when ended_at is missing."""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start=time(hour=0, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            external_id="contact-2", name="Other Contact"
        )
        self.room = Room.objects.create(contact=self.contact, queue=self.queue)
        Room.objects.filter(pk=self.room.pk).update(
            full_transfer_history=[
                {"action": "pick", "from": {}, "to": {}},
                {"action": "transfer", "from": {}, "to": {}},
            ]
        )
        self.room.refresh_from_db()

    def test_chip_timestamps_are_spaced_when_ended_at_is_none(self):
        data = BuildRoomExportData().execute(self.room)

        chips = [
            item
            for item in data["timeline"]
            if item["type"] == TIMELINE_ITEM_TRANSFER_CHIP
        ]
        self.assertEqual(len(chips), 2)
        self.assertLess(chips[0]["created_on"], chips[1]["created_on"])
