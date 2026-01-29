from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from chats.apps.accounts.models import User
from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.api.v1.internal.rooms.filters import RoomFilter
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class RoomFilterTestCase(TestCase):
    """
    Testes para o RoomFilter, especificamente o método filter_contact
    que deve ignorar acentos na busca.
    """

    def setUp(self):
        """Configura dados de teste comuns."""
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create_user(email="test@test.com")

        self.contact_angela = Contact.objects.create(
            name="Ângela Silva", email="angela@test.com"
        )
        self.contact_jose = Contact.objects.create(
            name="José Santos", email="jose@test.com"
        )
        self.contact_maria = Contact.objects.create(
            name="Maria Costa", email="maria@test.com"
        )
        self.contact_paulo = Contact.objects.create(
            name="Paulo Oliveira", email="paulo@test.com"
        )

        self.room_angela = Room.objects.create(
            contact=self.contact_angela,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
            urn="whatsapp:5511999999991",
        )
        self.room_jose = Room.objects.create(
            contact=self.contact_jose,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
            urn="whatsapp:5511999999992",
        )
        self.room_maria = Room.objects.create(
            contact=self.contact_maria,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
            urn="whatsapp:5511999999993",
        )
        self.room_paulo = Room.objects.create(
            contact=self.contact_paulo,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
            urn="whatsapp:5511999999994",
        )

    def test_filter_contact_ignores_accents(self):
        """
        Testa se a busca por "angela" (sem acento) encontra "Ângela" (com acento).
        """
        room_filter = RoomFilter(
            data={"contact": "angela", "project": str(self.project.uuid)},
            queryset=Room.objects.all(),
        )
        filtered_queryset = room_filter.qs

        self.assertIn(self.room_angela, filtered_queryset)
        self.assertEqual(filtered_queryset.count(), 1)

    def test_filter_contact_ignores_accents_jose(self):
        """
        Testa se a busca por "jose" (sem acento) encontra "José" (com acento).
        """
        room_filter = RoomFilter(
            data={"contact": "jose", "project": str(self.project.uuid)},
            queryset=Room.objects.all(),
        )
        filtered_queryset = room_filter.qs

        self.assertIn(self.room_jose, filtered_queryset)
        self.assertEqual(filtered_queryset.count(), 1)

    def test_filter_contact_case_insensitive(self):
        """
        Testa se a busca é case-insensitive.
        """
        room_filter = RoomFilter(
            data={"contact": "ANGELA", "project": str(self.project.uuid)},
            queryset=Room.objects.all(),
        )
        filtered_queryset = room_filter.qs

        self.assertIn(self.room_angela, filtered_queryset)

    def test_filter_contact_partial_match(self):
        """
        Testa se a busca parcial funciona (icontains).
        """
        room_filter = RoomFilter(
            data={"contact": "Silva", "project": str(self.project.uuid)},
            queryset=Room.objects.all(),
        )
        filtered_queryset = room_filter.qs

        self.assertIn(self.room_angela, filtered_queryset)

    def test_filter_contact_by_urn(self):
        """
        Testa se a busca também funciona pelo campo urn.
        """
        room_filter = RoomFilter(
            data={"contact": "5511999999991", "project": str(self.project.uuid)},
            queryset=Room.objects.all(),
        )
        filtered_queryset = room_filter.qs

        self.assertIn(self.room_angela, filtered_queryset)

    def test_filter_contact_no_matches(self):
        """
        Testa quando não há correspondências.
        """
        room_filter = RoomFilter(
            data={"contact": "inexistente", "project": str(self.project.uuid)},
            queryset=Room.objects.all(),
        )
        filtered_queryset = room_filter.qs

        self.assertEqual(filtered_queryset.count(), 0)


class InternalRoomsViewSetFilterTestCase(APITestCase):
    """
    Testes de integração para o endpoint v1/internal/rooms
    com o filtro de contato.
    """

    def setUp(self):
        """Configura dados de teste comuns."""
        self.user = User.objects.create_user(email="internal@vtex.com")
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

        self.contact = Contact.objects.create(
            name="Ângela Silva", email="angela@test.com"
        )
        self.room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )

        self.client.force_authenticate(self.user)

    @with_internal_auth
    def test_list_rooms_filter_contact_without_accent(self):
        """
        Testa se o endpoint retorna a sala quando buscar por nome sem acento.
        """
        response = self.client.get(
            "/v1/internal/rooms/",
            {
                "contact": "angela",
                "project": str(self.project.uuid),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["contact"]["name"], "Ângela Silva"
        )

    @with_internal_auth
    def test_list_rooms_filter_contact_case_insensitive(self):
        """
        Testa se o endpoint é case-insensitive.
        """
        response = self.client.get(
            "/v1/internal/rooms/",
            {
                "contact": "ANGELA",
                "project": str(self.project.uuid),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
