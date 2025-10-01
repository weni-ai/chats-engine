from rest_framework.test import APITestCase

from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response

from chats.apps.csat.models import CSATSurvey
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.api.authentication.token import JWTTokenGenerator


class BaseTestCSATWebhookView(APITestCase):
    def create(self, data: dict, token: str = None) -> Response:
        url = reverse("csat_internal-list")
        return self.client.post(
            url, data, format="json", HTTP_AUTHORIZATION=f"Token {token}"
        )


class TestCSATWebhookView(BaseTestCSATWebhookView):
    def setUp(self):
        self.jwt_generator = JWTTokenGenerator()
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(
            project_uuid=self.project.uuid, queue=self.queue
        )

    def test_cannot_create_csat_without_token(self):
        response = self.create(
            {"room": self.room.uuid, "rating": 5, "comment": "Test Comment"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_create_csat_with_token_from_another_project(self):
        project_2 = Project.objects.create(name="Test Project 2")

        token = self.jwt_generator.generate_token({"project": str(project_2.uuid)})

        response = self.create(
            {"room": self.room.uuid, "rating": 5, "comment": "Test Comment"},
            token=token,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
