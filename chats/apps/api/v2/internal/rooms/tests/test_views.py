from typing import Optional

from django.urls import reverse
from django.utils import timezone as django_timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class BaseTestInternalListRoomsViewSetV2(APITestCase):
    def list_rooms(self, params: Optional[dict] = None) -> Response:
        url = reverse("room_internal_v2-list")
        return self.client.get(url, params or {})

    def retrieve_room(self, room_uuid, params: Optional[dict] = None) -> Response:
        url = reverse("room_internal_v2-detail", kwargs={"uuid": str(room_uuid)})
        return self.client.get(url, params or {})


class TestInternalListRoomsViewSetV2AsAnonymousUser(BaseTestInternalListRoomsViewSetV2):
    def test_list_returns_401(self):
        response = self.list_rooms({"project": "00000000-0000-0000-0000-000000000001"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestInternalListRoomsViewSetV2AsAuthenticatedUser(
    BaseTestInternalListRoomsViewSetV2
):
    def setUp(self):
        self.user = User.objects.create_user(email="internal@vtex.com")
        self.project = Project.objects.create(
            name="Test Project V2 Rooms",
            timezone=str(django_timezone.get_current_timezone()),
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Maria", email="maria@test.com")
        self.room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )
        ProjectPermission.objects.create(
            user=self.user,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.client.force_authenticate(self.user)

    def test_list_without_internal_permission_returns_403(self):
        response = self.list_rooms({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_list_with_internal_permission_returns_200(self):
        response = self.list_rooms({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    @with_internal_auth
    def test_list_serializes_agent_sector_queue_as_objects(self):
        response = self.list_rooms({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = response.data["results"][0]

        self.assertIsInstance(row["agent"], dict)
        self.assertEqual(
            set(row["agent"].keys()),
            {"name", "email", "is_deleted"},
        )
        self.assertEqual(row["agent"]["email"], "internal@vtex.com")
        self.assertFalse(row["agent"]["is_deleted"])

        self.assertEqual(
            row["sector"],
            {"name": "Test Sector", "is_deleted": False},
        )
        self.assertEqual(
            row["queue"],
            {"name": "Test Queue", "is_deleted": False},
        )

    @with_internal_auth
    def test_retrieve_returns_200_and_same_payload_shape(self):
        response = self.retrieve_room(
            self.room.uuid,
            {"project": str(self.project.uuid)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(self.room.uuid))
        self.assertIsInstance(response.data["agent"], dict)
        self.assertEqual(
            set(response.data["agent"].keys()),
            {"name", "email", "is_deleted"},
        )
