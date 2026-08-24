from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorTag


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

    def test_can_filter_rooms_metrics_by_tag_name_and_sector(self):
        tag = SectorTag.objects.create(name="Atraso na Entrega", sector=self.sector)
        self.room.tags.add(tag)

        other_contact = Contact.objects.create(name="Other Contact")
        other_room = Room.objects.create(
            contact=other_contact,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )
        RoomMetrics.objects.create(room=other_room, waiting_time=5)

        other_sector = Sector.objects.create(
            name="Other Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)
        same_name_tag = SectorTag.objects.create(
            name="Atraso na Entrega",
            sector=other_sector,
        )
        other_sector_room = Room.objects.create(
            contact=Contact.objects.create(name="Other Sector Contact"),
            queue=other_queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )
        other_sector_room.tags.add(same_name_tag)
        RoomMetrics.objects.create(room=other_sector_room, waiting_time=5)

        response = self.list_rooms_metrics(
            {
                "sector": str(self.sector.uuid),
                "tag": "Atraso na Entrega",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(str(results[0]["uuid"]), str(self.room.uuid))
