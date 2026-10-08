from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from chats.apps.api.utils import create_user_and_token
from chats.apps.contacts.models import Contact
from chats.apps.contacts.usecases.out_off_whatsapp_response_window import (
    InvalidOutOffWindowFilter,
    build_out_off_window_contact_payload,
    out_off_whatsapp_response_window,
    parse_csv,
)
from chats.apps.msgs.models import Message
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

DEFAULT_ROOMS_LIMIT = 5
WHATSAPP_WINDOW_EXPIRED_DAYS = 2


class OutOffWhatsappResponseWindowUseCaseTests(TestCase):
    def setUp(self):
        self.user, _ = create_user_and_token("windowusecase")
        self.project = Project.objects.create(name="Window Project")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=DEFAULT_ROOMS_LIMIT,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)

    def _contact(self, name, external_id, email=""):
        return Contact.objects.create(name=name, external_id=external_id, email=email)

    def _room(
        self, contact, urn, queue=None, days_old=WHATSAPP_WINDOW_EXPIRED_DAYS, user=None
    ):
        room = Room.objects.create(
            queue=queue or self.queue,
            contact=contact,
            user=user,
            urn=urn,
            is_active=True,
        )
        Room.objects.filter(pk=room.pk).update(
            created_on=timezone.now() - timedelta(days=days_old)
        )
        room.refresh_from_db()
        return room

    def test_parse_csv_strips_empty_items(self):
        self.assertEqual(parse_csv(" a, ,b "), ["a", "b"])
        self.assertEqual(parse_csv(None), [])

    def test_invalid_sector_raises_before_listing(self):
        with self.assertRaises(InvalidOutOffWindowFilter):
            out_off_whatsapp_response_window(self.project, sectors=["not-a-uuid"])

    def test_payload_uses_external_id_and_hides_email(self):
        contact = self._contact("Maria", "ext-maria", email="maria@example.com")
        self._room(contact, "whatsapp:5500000000001")

        contacts, rooms = out_off_whatsapp_response_window(self.project)
        payload = build_out_off_window_contact_payload(list(contacts), rooms)

        self.assertEqual(len(payload), 1)
        self.assertEqual(set(payload[0].keys()), {"uuid", "name", "urns"})
        self.assertEqual(payload[0]["uuid"], "ext-maria")
        self.assertEqual(
            payload[0]["urns"],
            [{"scheme": "whatsapp", "path": "5500000000001"}],
        )

    def test_drops_non_whatsapp_recent_rooms_and_blank_external_id(self):
        self._room(self._contact("Mail", "ext-mail"), "mailto:mail@example.com")
        self._room(
            self._contact("Recent", "ext-recent"), "whatsapp:5500000000002", days_old=0
        )
        self._room(self._contact("No id", None), "whatsapp:5500000000003")
        expired = self._contact("Expired", "ext-expired")
        self._room(expired, "whatsapp:5500000000004")

        contacts, _ = out_off_whatsapp_response_window(self.project)
        self.assertEqual(
            list(contacts.values_list("external_id", flat=True)), ["ext-expired"]
        )

    def test_recent_contact_message_keeps_the_room_inside_the_window(self):
        contact = self._contact("Maria", "ext-maria")
        room = self._room(contact, "whatsapp:5500000000001", days_old=0)
        Message.objects.create(room=room, contact=contact, text="oi")
        Room.objects.filter(pk=room.pk).update(
            created_on=timezone.now() - timedelta(days=WHATSAPP_WINDOW_EXPIRED_DAYS)
        )

        contacts, _ = out_off_whatsapp_response_window(self.project)
        self.assertEqual(contacts.count(), 0)

    def test_agent_message_does_not_keep_the_window_open(self):
        contact = self._contact("Maria", "ext-maria")
        room = self._room(contact, "whatsapp:5500000000001", days_old=0, user=self.user)
        Message.objects.create(room=room, user=self.user, text="oi")
        Room.objects.filter(pk=room.pk).update(
            created_on=timezone.now() - timedelta(days=WHATSAPP_WINDOW_EXPIRED_DAYS)
        )

        contacts, _ = out_off_whatsapp_response_window(self.project)
        self.assertEqual(
            list(contacts.values_list("external_id", flat=True)), ["ext-maria"]
        )

    def test_filters_by_queue_user_and_search(self):
        other_user, _ = create_user_and_token("otherwindow")
        other_sector = Sector.objects.create(
            name="Other",
            project=self.project,
            rooms_limit=DEFAULT_ROOMS_LIMIT,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other queue", sector=other_sector)
        self._room(
            self._contact("Maria", "ext-maria"),
            "whatsapp:5500000000001",
            user=self.user,
        )
        self._room(
            self._contact("Other", "ext-other"),
            "whatsapp:5500000000002",
            user=other_user,
        )
        self._room(
            self._contact("Other queue", "ext-queue"),
            "whatsapp:5500000000003",
            queue=other_queue,
            user=self.user,
        )

        contacts, _ = out_off_whatsapp_response_window(
            self.project,
            sectors=[str(self.sector.uuid)],
            queues=[str(self.queue.uuid)],
            user_email=self.user.email,
            search="maria",
        )
        self.assertEqual(
            list(contacts.values_list("external_id", flat=True)), ["ext-maria"]
        )

    def test_joins_distinct_urns_for_the_same_contact(self):
        contact = self._contact("Maria", "ext-maria")
        other_sector = Sector.objects.create(
            name="Other",
            project=self.project,
            rooms_limit=DEFAULT_ROOMS_LIMIT,
            work_start="09:00",
            work_end="18:00",
        )
        second_queue = Queue.objects.create(name="Second queue", sector=other_sector)
        third_sector = Sector.objects.create(
            name="Third",
            project=self.project,
            rooms_limit=DEFAULT_ROOMS_LIMIT,
            work_start="09:00",
            work_end="18:00",
        )
        third_queue = Queue.objects.create(name="Third queue", sector=third_sector)
        self._room(contact, "whatsapp:5500000000002")
        self._room(contact, "whatsapp:5500000000002", queue=second_queue)
        self._room(contact, "whatsapp:5500000000001", queue=third_queue)

        contacts, rooms = out_off_whatsapp_response_window(self.project)
        payload = build_out_off_window_contact_payload(list(contacts), rooms)

        self.assertEqual(contacts.count(), 1)
        self.assertEqual(
            payload[0]["urns"],
            [
                {"scheme": "whatsapp", "path": "5500000000001"},
                {"scheme": "whatsapp", "path": "5500000000002"},
            ],
        )
