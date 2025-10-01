import uuid
from unittest.mock import patch
from rest_framework.test import APITestCase

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from chats.apps.api.v1.internal.csat.tests.decorators import (
    with_closed_room,
    with_project_jwt_token,
)
from chats.apps.csat.models import CSATSurvey
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.api.authentication.token import JWTTokenGenerator


class BaseTestCSATWebhookView(APITestCase):
    def create(self, data: dict, token: str = None) -> Response:
        url = reverse("csat_internal-list")

        if not token and hasattr(self, "token") and self.token:
            token = self.token

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
            project_uuid=self.project.uuid,
            queue=self.queue,
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

    @with_project_jwt_token
    def test_cannot_create_csat_for_non_existent_room(self):
        response = self.create(
            {"room": uuid.uuid4(), "rating": 5, "comment": "Test Comment"}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_jwt_token
    def test_cannot_create_csat_for_active_room(self):
        response = self.create(
            {"room": self.room.uuid, "rating": 5, "comment": "Test Comment"}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_jwt_token
    @with_closed_room
    def test_create_csat(self):
        payload = {
            "room": self.room.uuid,
            "rating": 5,
            "comment": "Test Comment",
        }

        now = timezone.now()

        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = now
            response = self.create(payload)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        csat = CSATSurvey.objects.first()

        self.assertIsNotNone(csat)
        self.assertEqual(csat.room, self.room)
        self.assertEqual(csat.rating, payload["rating"])
        self.assertEqual(csat.comment, payload["comment"])
        self.assertEqual(csat.answered_on, now)

    @with_project_jwt_token
    @with_closed_room
    def test_cannot_create_csat_with_invalid_rating_above_max_value(self):
        response = self.create(
            {"room": self.room.uuid, "rating": 6, "comment": "Test Comment"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["rating"][0].code, "max_value")

    @with_project_jwt_token
    @with_closed_room
    def test_cannot_create_csat_with_invalid_rating_below_min_value(self):
        response = self.create(
            {"room": self.room.uuid, "rating": 0, "comment": "Test Comment"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["rating"][0].code, "min_value")

    @with_project_jwt_token
    @with_closed_room
    def test_create_csat_without_comment(self):
        response = self.create({"room": self.room.uuid, "rating": 5})

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
