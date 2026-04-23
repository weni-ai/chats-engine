import uuid

from django.urls import reverse
from parameterized import parameterized
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


SECTOR_UUID = "21aecf8c-0c73-4059-ba82-4343e0cc627c"
QUEUE_UUID = "f2519480-7e58-4fc4-9894-9ab1769e29cf"


class RoomsCountTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.user = User.objects.get(pk=8)
        self.token = Token.objects.get(user=self.user)
        self.sector = Sector.objects.get(pk=SECTOR_UUID)
        self.queue = Queue.objects.get(uuid=QUEUE_UUID)
        self.agent = User.objects.get(pk=6)

        Room.objects.filter(queue__sector=self.sector).update(is_active=False)

        self.url = reverse("rooms-count")

    def _get(self, params, token=None):
        token = token or self.token.key
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)
        return self.client.get(self.url, params)

    def _build_params(self, scope):
        if scope == "sector":
            return {"sector": str(self.sector.pk)}
        return {"queue": str(self.queue.pk)}

    @parameterized.expand([("sector",), ("queue",)])
    def test_no_rooms(self, scope):
        response = self._get(self._build_params(scope))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["waiting"], 0)
        self.assertEqual(response.data["in_service"], 0)

    @parameterized.expand([("sector",), ("queue",)])
    def test_rooms_count_with_waiting_and_in_service(self, scope):
        contact_waiting = Contact.objects.create(name="Waiting Contact")
        contact_service = Contact.objects.create(name="Service Contact")
        Room.objects.create(
            queue=self.queue, contact=contact_waiting, is_active=True
        )
        Room.objects.create(
            queue=self.queue,
            contact=contact_service,
            user=self.agent,
            is_active=True,
        )

        response = self._get(self._build_params(scope))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["waiting"], 1)
        self.assertEqual(response.data["in_service"], 1)

    @parameterized.expand([("sector",), ("queue",)])
    def test_rooms_count_ignores_closed_rooms(self, scope):
        contact_active = Contact.objects.create(name="Active Contact")
        contact_closed = Contact.objects.create(name="Closed Contact")
        Room.objects.create(
            queue=self.queue, contact=contact_active, is_active=True
        )
        closed_room = Room.objects.create(
            queue=self.queue, contact=contact_closed, is_active=True
        )
        closed_room.is_active = False
        closed_room.save(update_fields=["is_active"])

        response = self._get(self._build_params(scope))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["waiting"], 1)
        self.assertEqual(response.data["in_service"], 0)

    def test_unauthenticated(self):
        response = self.client.get(self.url, {"sector": str(self.sector.pk)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_params(self):
        response = self._get({})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_both_params(self):
        response = self._get(
            {"sector": str(self.sector.pk), "queue": str(self.queue.pk)}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_uuid(self):
        response = self._get({"sector": "not-a-uuid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_sector_returns_zero_counts(self):
        response = self._get({"sector": str(uuid.uuid4())})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["waiting"], 0)
        self.assertEqual(response.data["in_service"], 0)
