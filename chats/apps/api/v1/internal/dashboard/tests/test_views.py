import uuid
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.dashboard.dto import CSATRatingCount, CSATRatings
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.accounts.tests.decorators import with_internal_auth


class BaseTestInternalDashboardView(APITestCase):
    def get_csat_ratings(self, project_uuid: str, filters: dict = {}) -> Response:
        url = f"/v1/internal/dashboard/{project_uuid}/csat_ratings/"

        return self.client.get(url, filters)


class TestInternalDashboardViewUnauthenticated(BaseTestInternalDashboardView):
    def test_csat_ratings_unauthenticated(self):
        response = self.get_csat_ratings(uuid.uuid4(), {})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestInternalDashboardViewAuthenticated(BaseTestInternalDashboardView):
    def setUp(self):
        self.user = User.objects.create(email="testuser@test.com")
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Test Sector",
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue = Queue.objects.create(sector=self.sector, name="Test Queue")

        self.client.force_authenticate(user=self.user)

    def test_csat_ratings_without_permission(self):
        response = self.get_csat_ratings(self.project.uuid, {})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    @patch("chats.apps.api.v1.internal.dashboard.service.CSATService.get_csat_ratings")
    def test_csat_ratings_authenticated(self, mock_get_csat_ratings):
        mock_get_csat_ratings.return_value = CSATRatings(
            ratings=[CSATRatingCount(rating=5, count=1, percentage=100)]
        )
        response = self.get_csat_ratings(self.project.uuid, {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["csat_ratings"],
            [
                {
                    "rating": 5,
                    "value": 100.0,
                    "full_value": 1,
                }
            ],
        )
