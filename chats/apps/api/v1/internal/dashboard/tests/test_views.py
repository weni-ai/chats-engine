import uuid

from django.db.models import Avg, Count
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response
from rest_framework.request import Request

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.dashboard.dto import CSATScoreGeneral
from chats.apps.projects.models.models import Project
from chats.apps.accounts.tests.decorators import with_internal_auth
from unittest.mock import patch


class BaseTestInternalDashboardView(APITestCase):
    def get_agent_csat_metrics(self, project_uuid: str, filters: dict = {}) -> Response:
        url = f"/v1/internal/dashboard/{project_uuid}/csat-score-by-agents/"

        return self.client.get(url, filters)


class TestInternalDashboardViewUnauthenticated(BaseTestInternalDashboardView):
    def test_get_agent_csat_metrics_unauthenticated(self):
        response = self.get_agent_csat_metrics(uuid.uuid4())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestInternalDashboardViewAuthenticated(BaseTestInternalDashboardView):
    def setUp(self):
        self.user = User.objects.create(email="testuser@test.com")
        self.project = Project.objects.create(name="Test Project")

        self.client.force_authenticate(user=self.user)

    @with_internal_auth
    @patch(
        "chats.apps.api.v1.internal.dashboard.viewsets.AgentsService.get_agents_csat_score"
    )
    def test_get_agent_csat_metrics_authenticated(self, mock_get_agents_csat_score):
        users = [
            User.objects.create(email="agent1@test.com"),
            User.objects.create(email="agent2@test.com"),
        ]

        mock_get_agents_csat_score.return_value = (
            CSATScoreGeneral(rooms=10, reviews=5, avg_rating=4.5),
            User.objects.filter(email__in=["agent1@test.com", "agent2@test.com"])
            .annotate(
                rooms_count=Count("rooms__uuid", distinct=True),
                reviews=Count("rooms__csat_survey__rating", distinct=True),
                avg_rating=Avg("rooms__csat_survey__rating"),
            )
            .values("rooms_count", "reviews", "avg_rating"),
        )

        response = self.get_agent_csat_metrics(self.project.uuid, {"page_size": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["general"],
            {
                "rooms": 10,
                "reviews": 5,
                "avg_rating": 4.5,
            },
        )
        self.assertEqual(
            response.data["results"],
            [
                {
                    "agent": "agent1@test.com",
                    "rooms": 5,
                    "reviews": 3,
                    "avg_rating": 5.0,
                }
            ],
        )
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
