from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class RoomFilterQueuesAndSectorsTests(APITestCase):
    def setUp(self):
        self.url = reverse("room-list")

        self.project = Project.objects.create(name="Filter Project")
        self.user = User.objects.create_user(email="agent@test.com")
        self.permission = ProjectPermission.objects.create(
            user=self.user,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )

        self.sector_a = Sector.objects.create(
            name="Sector A",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_b = Sector.objects.create(
            name="Sector B",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )

        self.queue_a1 = Queue.objects.create(name="A1", sector=self.sector_a)
        self.queue_a2 = Queue.objects.create(name="A2", sector=self.sector_a)
        self.queue_b1 = Queue.objects.create(name="B1", sector=self.sector_b)

        for queue in (self.queue_a1, self.queue_a2, self.queue_b1):
            QueueAuthorization.objects.create(
                permission=self.permission,
                queue=queue,
                role=QueueAuthorization.ROLE_AGENT,
            )

        self.room_a1 = Room.objects.create(
            queue=self.queue_a1,
            contact=Contact.objects.create(),
            is_active=True,
        )
        self.room_a2 = Room.objects.create(
            queue=self.queue_a2,
            contact=Contact.objects.create(),
            is_active=True,
        )
        self.room_b1 = Room.objects.create(
            queue=self.queue_b1,
            contact=Contact.objects.create(),
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

    def _list(self, params):
        return self.client.get(self.url, params)

    def _uuids(self, response):
        return {r["uuid"] for r in response.data["results"]}

    @patch("chats.apps.api.v1.rooms.viewsets.is_feature_active", return_value=False)
    def test_queues_filter_returns_union_of_rooms(self, _):
        response = self._list({
            "project": str(self.project.uuid),
            "queues": f"{self.queue_a1.uuid},{self.queue_b1.uuid}",
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self._uuids(response),
            {str(self.room_a1.uuid), str(self.room_b1.uuid)},
        )

    @patch("chats.apps.api.v1.rooms.viewsets.is_feature_active", return_value=False)
    def test_queues_filter_with_single_uuid(self, _):
        response = self._list({
            "project": str(self.project.uuid),
            "queues": str(self.queue_a1.uuid),
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._uuids(response), {str(self.room_a1.uuid)})

    @patch("chats.apps.api.v1.rooms.viewsets.is_feature_active", return_value=False)
    def test_queues_filter_invalid_uuid_returns_400(self, _):
        response = self._list({
            "project": str(self.project.uuid),
            "queues": "not-a-uuid",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.api.v1.rooms.viewsets.is_feature_active", return_value=False)
    def test_existing_queue_filter_still_works(self, _):
        response = self._list({
            "project": str(self.project.uuid),
            "queue": str(self.queue_a1.uuid),
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._uuids(response), {str(self.room_a1.uuid)})

    @patch("chats.apps.api.v1.rooms.viewsets.is_feature_active", return_value=False)
    def test_sectors_filter_returns_rooms_from_all_sector_queues(self, _):
        response = self._list({
            "project": str(self.project.uuid),
            "sectors": str(self.sector_a.uuid),
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self._uuids(response),
            {str(self.room_a1.uuid), str(self.room_a2.uuid)},
        )

    @patch("chats.apps.api.v1.rooms.viewsets.is_feature_active", return_value=False)
    def test_sectors_filter_supports_multiple_uuids(self, _):
        response = self._list({
            "project": str(self.project.uuid),
            "sectors": f"{self.sector_a.uuid},{self.sector_b.uuid}",
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self._uuids(response),
            {
                str(self.room_a1.uuid),
                str(self.room_a2.uuid),
                str(self.room_b1.uuid),
            },
        )

    @patch("chats.apps.api.v1.rooms.viewsets.is_feature_active", return_value=False)
    def test_queues_and_sectors_combined(self, _):
        response = self._list({
            "project": str(self.project.uuid),
            "queues": str(self.queue_a1.uuid),
            "sectors": str(self.sector_a.uuid),
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._uuids(response), {str(self.room_a1.uuid)})


class RoomFilterQueuesPermissionScopingTests(APITestCase):
    """
    The `queues` filter is additive over the queryset already restricted by
    the user's `queue_authorizations`, so an attendant cannot peek into
    queues they don't belong to even by passing their UUIDs.
    """

    def setUp(self):
        self.url = reverse("room-list")
        self.project = Project.objects.create(name="Scoping Project")

        self.attendant = User.objects.create_user(email="attendant@test.com")
        attendant_permission = ProjectPermission.objects.create(
            user=self.attendant,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.allowed_queue = Queue.objects.create(name="Allowed", sector=sector)
        self.forbidden_queue = Queue.objects.create(name="Forbidden", sector=sector)

        QueueAuthorization.objects.create(
            permission=attendant_permission,
            queue=self.allowed_queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        self.allowed_room = Room.objects.create(
            queue=self.allowed_queue,
            contact=Contact.objects.create(),
            is_active=True,
        )
        self.forbidden_room = Room.objects.create(
            queue=self.forbidden_queue,
            contact=Contact.objects.create(),
            is_active=True,
        )

        self.client.force_authenticate(user=self.attendant)

    @patch("chats.apps.api.v1.rooms.viewsets.is_feature_active", return_value=False)
    def test_attendant_cannot_see_rooms_from_forbidden_queue_via_queues_filter(
        self, _
    ):
        response = self.client.get(
            self.url,
            {
                "project": str(self.project.uuid),
                "queues": f"{self.allowed_queue.uuid},{self.forbidden_queue.uuid}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        uuids = {r["uuid"] for r in response.data["results"]}
        self.assertIn(str(self.allowed_room.uuid), uuids)
        self.assertNotIn(str(self.forbidden_room.uuid), uuids)
