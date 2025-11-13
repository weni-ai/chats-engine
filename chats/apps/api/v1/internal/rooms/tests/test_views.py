from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.contacts.models import Contact


class BaseTestInternalProtocolRoomsViewSet(APITestCase):
    def list_protocols(self, filters: dict = {}) -> Response:
        url = f"/v1/internal/rooms/protocols/"
        return self.client.get(url, filters)


class TestInternalProtocolRoomsViewSetAsAnonymousUser(
    BaseTestInternalProtocolRoomsViewSet
):
    def test_list_protocols_without_authentication(self):
        response = self.list_protocols()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestInternalProtocolRoomsViewSetAsAuthenticatedUser(
    BaseTestInternalProtocolRoomsViewSet
):
    def setUp(self):
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
        self.room_with_protocol = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact", email="test@test.com"),
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
            protocol="test",
        )
        self.room_without_protocol = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact", email="test@test.com"),
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )

        self.client.force_authenticate(self.user)

    def test_list_protocols_without_permission(self):
        response = self.list_protocols()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_list_protocols_with_permission(self):
        response = self.list_protocols({"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["protocol"], self.room_with_protocol.protocol
        )
