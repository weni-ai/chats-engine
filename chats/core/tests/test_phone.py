from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.core.phone import build_urn_lookup_q, phone_urn_q


class PhoneUrnQTests(TestCase):
    def test_returns_none_for_short_terms(self):
        self.assertIsNone(phone_urn_q("1234567"))

    def test_returns_none_for_foreign_numbers(self):
        self.assertIsNone(phone_urn_q("+12025550123"))

    def test_matches_without_ninth_digit_when_searching_with_ninth(self):
        project = Project.objects.create(name="Phone Project")
        sector = Sector.objects.create(
            name="Sector",
            project=project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        queue = Queue.objects.create(name="Queue", sector=sector)
        contact = Contact.objects.create(name="Contact")
        room = Room.objects.create(
            contact=contact,
            queue=queue,
            urn="whatsapp:558492126050",
        )

        matches = Room.objects.filter(phone_urn_q("992126050"))
        self.assertIn(room, matches)

    def test_matches_with_ninth_digit_when_searching_without_ninth(self):
        project = Project.objects.create(name="Phone Project")
        sector = Sector.objects.create(
            name="Sector",
            project=project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        queue = Queue.objects.create(name="Queue", sector=sector)
        contact = Contact.objects.create(name="Contact")
        room = Room.objects.create(
            contact=contact,
            queue=queue,
            urn="whatsapp:5584992126050",
        )

        matches = Room.objects.filter(phone_urn_q("992126050"))
        self.assertIn(room, matches)

    def test_respects_ddd_when_provided(self):
        project = Project.objects.create(name="Phone Project")
        sector = Sector.objects.create(
            name="Sector",
            project=project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        queue = Queue.objects.create(name="Queue", sector=sector)
        contact = Contact.objects.create(name="Contact")
        room_84 = Room.objects.create(
            contact=contact,
            queue=queue,
            urn="whatsapp:5584992126050",
        )
        other_contact = Contact.objects.create(name="Other")
        room_11 = Room.objects.create(
            contact=other_contact,
            queue=queue,
            urn="whatsapp:5511992126050",
        )

        matches = Room.objects.filter(phone_urn_q("84992126050"))
        self.assertIn(room_84, matches)
        self.assertNotIn(room_11, matches)

    def test_nested_field_lookup(self):
        project = Project.objects.create(name="Phone Project")
        sector = Sector.objects.create(
            name="Sector",
            project=project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        queue = Queue.objects.create(name="Queue", sector=sector)
        contact = Contact.objects.create(name="Contact")
        Room.objects.create(
            contact=contact,
            queue=queue,
            urn="whatsapp:5584992126050",
        )

        matches = Contact.objects.filter(phone_urn_q("992126050", field="rooms__urn"))
        self.assertEqual(matches.count(), 1)


class BuildUrnLookupQTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Lookup Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.user = User.objects.create_user(email="lookup@test.com")
        self.contact = Contact.objects.create(name="Lookup Contact")
        self.room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.user,
            urn="whatsapp:5584992126050",
        )

    def test_fallback_still_matches_partial_urn(self):
        matches = Room.objects.filter(
            build_urn_lookup_q("992126050", ninth_digit_enabled=True)
        )
        self.assertIn(self.room, matches)

    def test_lookup_without_flag_uses_icontains_only(self):
        room_without_nine = Room.objects.create(
            contact=Contact.objects.create(name="Without Nine"),
            queue=self.queue,
            user=self.user,
            urn="whatsapp:558492126050",
        )
        matches = Room.objects.filter(
            build_urn_lookup_q("992126050", ninth_digit_enabled=False)
        )
        self.assertNotIn(room_without_nine, matches)
