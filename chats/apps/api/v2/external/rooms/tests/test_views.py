from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector
from chats.apps.rooms.models import Room
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.contacts.models import Contact


class BaseTestExternalRoomMetrics(APITestCase):
    def list_rooms_metrics(self, filters: dict = {}) -> Response:
        url = reverse("external_rooms_metrics_v2-list")

        return self.client.get(url, filters)


class TestExternalRoomMetricsAsAnonymousUser(BaseTestExternalRoomMetrics):
    def test_cannot_list_rooms_metrics_as_anonymous_user(self):
        response = self.list_rooms_metrics()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestExternalRoomMetrics(BaseTestExternalRoomMetrics):
    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com")
        self.project = Project.objects.create(name="Test Project")

        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Test Contact")
        self.room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )
        self.metrics = RoomMetrics.objects.create(room=self.room, waiting_time=10)

        self.token = str(self.project.external_token.uuid)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_can_list_rooms_metrics(self):

        response = self.list_rooms_metrics()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
