from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

DEFAULT_ROOMS_LIMIT = 5


class OutOffWhatsappResponseWindowContactsTests(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("windowagent")
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
        self.url = reverse("contacts-out-off-whatsapp-response-window")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def _contact(self, name, external_id, email="", document=""):
        return Contact.objects.create(
            name=name,
            external_id=external_id,
            email=email,
            document=document,
        )

    def _room(self, contact, urn, queue=None, days_old=2, user=None, is_active=True):
        room = Room.objects.create(
            queue=queue or self.queue,
            contact=contact,
            user=user,
            urn=urn,
            is_active=is_active,
        )
        Room.objects.filter(pk=room.pk).update(
            created_on=timezone.now() - timedelta(days=days_old)
        )
        room.refresh_from_db()
        return room

    def _get(self, **params):
        params.setdefault("project", str(self.project.uuid))
        return self.client.get(self.url, params)

    def test_requires_project(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_project_returns_404(self):
        response = self._get(project="00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_without_permission_returns_404(self):
        _, token = create_user_and_token("outsider")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self._get()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_lists_contact_outside_the_window(self):
        contact = self._contact(
            "Maria",
            "ext-maria",
            email="maria@example.com",
            document="12345678900",
        )
        self._room(contact, "whatsapp:5500000000001")

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(set(result.keys()), {"uuid", "name", "urns"})
        self.assertEqual(result["uuid"], "ext-maria")
        self.assertEqual(result["name"], "Maria")
        self.assertEqual(
            result["urns"], [{"scheme": "whatsapp", "path": "5500000000001"}]
        )

    def test_hides_contact_with_a_recent_contact_message(self):
        contact = self._contact("Maria", "ext-maria")
        room = self._room(contact, "whatsapp:5500000000001", days_old=0)
        Message.objects.create(room=room, contact=contact, text="oi")
        Room.objects.filter(pk=room.pk).update(
            created_on=timezone.now() - timedelta(days=2)
        )

        response = self._get()
        self.assertEqual(response.data["count"], 0)

    def test_hides_urn_when_another_room_has_a_recent_contact_message(self):
        contact = self._contact("Maria", "ext-maria")
        self._room(contact, "whatsapp:5500000000001")
        other = self._room(contact, "whatsapp:5500000000001", days_old=0)
        Message.objects.create(room=other, contact=contact, text="oi")
        Room.objects.filter(pk=other.pk).update(
            created_on=timezone.now() - timedelta(days=2)
        )

        response = self._get()
        self.assertEqual(response.data["count"], 0)

    def test_hides_urn_when_a_newer_room_of_the_same_urn_exists(self):
        contact = self._contact("Maria", "ext-maria")
        self._room(contact, "whatsapp:5500000000001")
        self._room(contact, "whatsapp:5500000000001", days_old=0)

        response = self._get()
        self.assertEqual(response.data["count"], 0)

    def test_ignores_non_whatsapp_and_recent_rooms(self):
        mail_contact = self._contact("Mail", "ext-mail")
        self._room(mail_contact, "mailto:mail@example.com")
        recent_contact = self._contact("Recent", "ext-recent")
        self._room(recent_contact, "whatsapp:5500000000002", days_old=0)

        response = self._get()
        self.assertEqual(response.data["count"], 0)

    def test_agent_message_does_not_keep_the_window_open(self):
        contact = self._contact("Maria", "ext-maria")
        room = self._room(contact, "whatsapp:5500000000001", days_old=0)
        Message.objects.create(room=room, user=self.user, text="oi")
        Room.objects.filter(pk=room.pk).update(
            created_on=timezone.now() - timedelta(days=2)
        )

        response = self._get()
        self.assertEqual(response.data["count"], 1)

    def test_groups_urns_of_the_same_contact(self):
        contact = self._contact("Maria", "ext-maria")
        other_sector = Sector.objects.create(
            name="Other",
            project=self.project,
            rooms_limit=DEFAULT_ROOMS_LIMIT,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other queue", sector=other_sector)
        self._room(contact, "whatsapp:5500000000001")
        self._room(contact, "whatsapp:5500000000002", queue=other_queue)

        response = self._get()

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["urns"],
            [
                {"scheme": "whatsapp", "path": "5500000000001"},
                {"scheme": "whatsapp", "path": "5500000000002"},
            ],
        )

    def test_filters_by_sector_and_queue(self):
        other_sector = Sector.objects.create(
            name="Other",
            project=self.project,
            rooms_limit=DEFAULT_ROOMS_LIMIT,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other queue", sector=other_sector)
        in_sector = self._contact("In sector", "ext-in-sector")
        in_queue = self._contact("In queue", "ext-in-queue")
        self._room(in_sector, "whatsapp:5500000000001", queue=other_queue)
        self._room(in_queue, "whatsapp:5500000000002")

        by_sector = self._get(sectors=str(other_sector.uuid))
        self.assertEqual(
            [item["uuid"] for item in by_sector.data["results"]],
            ["ext-in-sector"],
        )

        by_queue = self._get(queues=str(self.queue.uuid))
        self.assertEqual(
            [item["uuid"] for item in by_queue.data["results"]],
            ["ext-in-queue"],
        )

    def test_invalid_sector_returns_400(self):
        response = self._get(sectors="not-a-uuid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_by_name(self):
        self._room(self._contact("Maria", "ext-maria"), "whatsapp:5500000000001")
        self._room(self._contact("Joao", "ext-joao"), "whatsapp:5500000000002")

        response = self._get(search="maria")
        self.assertEqual(
            [item["uuid"] for item in response.data["results"]],
            ["ext-maria"],
        )

    def test_paginates_with_limit_and_offset(self):
        self._room(self._contact("Ana", "ext-ana"), "whatsapp:5500000000001")
        self._room(self._contact("Bruno", "ext-bruno"), "whatsapp:5500000000002")

        response = self._get(limit=1, offset=1)

        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["uuid"], "ext-bruno")

    def test_excludes_other_projects_and_contacts_without_external_id(self):
        other_project = Project.objects.create(name="Other")
        other_sector = Sector.objects.create(
            name="Other",
            project=other_project,
            rooms_limit=DEFAULT_ROOMS_LIMIT,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other queue", sector=other_sector)
        self._room(
            self._contact("Other", "ext-other"),
            "whatsapp:5500000000009",
            queue=other_queue,
        )
        self._room(self._contact("No external", None), "whatsapp:5500000000008")

        response = self._get()
        self.assertEqual(response.data["count"], 0)
