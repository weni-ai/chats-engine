from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.api.v1.internal.rooms.filters import RoomFilter
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorTag


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

    def _filter_contact(self, contact_term, ninth_digit_enabled=True):
        request = MagicMock()
        request.query_params = {"project": str(self.project.uuid)}
        request.user.email = "test@test.com"
        request.user.is_authenticated = True
        with patch(
            "chats.apps.api.v1.internal.rooms.filters.ninth_digit_search_enabled_from_request",
            return_value=ninth_digit_enabled,
        ):
            room_filter = RoomFilter(
                data={"contact": contact_term, "project": str(self.project.uuid)},
                queryset=Room.objects.all(),
                request=request,
            )
            return room_filter.qs

    def test_filter_contact_finds_room_without_ninth_digit(self):
        contact = Contact.objects.create(name="Nine Digit Contact")
        room = Room.objects.create(
            contact=contact,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
            urn="whatsapp:5584992126050",
        )
        self.assertIn(room, self._filter_contact("992126050"))

    def test_filter_contact_finds_room_with_ninth_digit(self):
        contact = Contact.objects.create(name="No Nine Digit Contact")
        room = Room.objects.create(
            contact=contact,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
            urn="whatsapp:558492126050",
        )
        self.assertIn(room, self._filter_contact("992126050"))

    def test_filter_contact_without_flag_does_not_find_room_without_ninth_digit(self):
        contact = Contact.objects.create(name="No Nine Digit Contact")
        room = Room.objects.create(
            contact=contact,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
            urn="whatsapp:558492126050",
        )
        self.assertNotIn(
            room, self._filter_contact("992126050", ninth_digit_enabled=False)
        )

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

    def test_filter_tag_name_without_sector_matches_all_sectors(self):
        tag = SectorTag.objects.create(name="Cancelamento - NC", sector=self.sector)
        self.room_angela.tags.add(tag)

        other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)
        same_name_tag = SectorTag.objects.create(
            name="Cancelamento - NC",
            sector=other_sector,
        )
        other_room = Room.objects.create(
            contact=Contact.objects.create(name="Other Sector Contact"),
            queue=other_queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )
        other_room.tags.add(same_name_tag)

        room_filter = RoomFilter(
            data={"tag_name": "Cancelamento - NC", "project": str(self.project.uuid)},
            queryset=Room.objects.all(),
        )
        filtered = list(room_filter.qs)

        self.assertIn(self.room_angela, filtered)
        self.assertIn(other_room, filtered)
        self.assertEqual(len(filtered), 2)

    def test_filter_tag_name_with_sector_restricts_to_sector(self):
        tag = SectorTag.objects.create(name="Cancelamento - NC", sector=self.sector)
        self.room_angela.tags.add(tag)

        other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)
        same_name_tag = SectorTag.objects.create(
            name="Cancelamento - NC",
            sector=other_sector,
        )
        other_room = Room.objects.create(
            contact=Contact.objects.create(name="Other Sector Contact"),
            queue=other_queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )
        other_room.tags.add(same_name_tag)

        room_filter = RoomFilter(
            data={
                "tag_name": "Cancelamento - NC",
                "sector": str(self.sector.uuid),
                "project": str(self.project.uuid),
            },
            queryset=Room.objects.all(),
        )
        filtered = list(room_filter.qs)

        self.assertEqual(filtered, [self.room_angela])
        self.assertNotIn(other_room, filtered)

    def test_filter_tag_name_unknown_returns_empty(self):
        room_filter = RoomFilter(
            data={"tag_name": "Tag Inexistente", "project": str(self.project.uuid)},
            queryset=Room.objects.all(),
        )
        self.assertEqual(room_filter.qs.count(), 0)

    def test_filter_without_tag_name_keeps_all_project_rooms(self):
        room_filter = RoomFilter(
            data={"project": str(self.project.uuid)},
            queryset=Room.objects.all(),
        )
        self.assertEqual(room_filter.qs.count(), 4)

    def test_filter_tag_name_combines_with_ended_at(self):
        now = timezone.now()
        tag = SectorTag.objects.create(name="Cancelamento - NC", sector=self.sector)
        self.room_angela.is_active = False
        self.room_angela.ended_at = now
        self.room_angela.save(update_fields=["is_active", "ended_at"])
        self.room_angela.tags.add(tag)

        self.room_jose.is_active = False
        self.room_jose.ended_at = now
        self.room_jose.save(update_fields=["is_active", "ended_at"])

        room_filter = RoomFilter(
            data={
                "project": str(self.project.uuid),
                "is_active": False,
                "tag_name": "Cancelamento - NC",
                "ended_at__gte": (now - timedelta(days=1)).isoformat(),
                "ended_at__lte": (now + timedelta(days=1)).isoformat(),
            },
            queryset=Room.objects.all(),
        )
        filtered = list(room_filter.qs)

        self.assertEqual(filtered, [self.room_angela])


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
        self.assertEqual(response.data["results"][0]["contact"], "Ângela Silva")

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

    @with_internal_auth
    def test_list_rooms_filter_by_tag_name(self):
        tag = SectorTag.objects.create(name="Cancelamento - NC", sector=self.sector)
        self.room.tags.add(tag)
        other = Room.objects.create(
            contact=Contact.objects.create(name="Other"),
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )

        response = self.client.get(
            "/v1/internal/rooms/",
            {
                "project": str(self.project.uuid),
                "tag_name": "Cancelamento - NC",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        uuids = {row["uuid"] for row in response.data["results"]}
        self.assertIn(str(self.room.uuid), uuids)
        self.assertNotIn(str(other.uuid), uuids)
