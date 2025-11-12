from unittest.mock import patch
import uuid

from django.utils import timezone
import pytz
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.dashboard.dto import CSATRatingCount, CSATRatings
from chats.apps.projects.models.models import (
    CustomStatus,
    CustomStatusType,
    Project,
    ProjectPermission,
)
from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector
from chats.apps.rooms.models import Room
from chats.apps.csat.models import CSATSurvey


class BaseTestInternalDashboardView(APITestCase):
    def get_agent_csat_metrics(self, project_uuid: str, filters: dict = {}) -> Response:
        url = f"/v1/internal/dashboard/{project_uuid}/csat-score-by-agents/"

        return self.client.get(url, filters)

    def get_csat_ratings(self, project_uuid: str, filters: dict = {}) -> Response:
        url = f"/v1/internal/dashboard/{project_uuid}/csat_ratings/"

        return self.client.get(url, filters)


class TestInternalDashboardViewUnauthenticated(BaseTestInternalDashboardView):
    def test_get_agent_csat_metrics_unauthenticated(self):
        response = self.get_agent_csat_metrics(uuid.uuid4())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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

    @with_internal_auth
    def test_get_agent_csat_metrics_authenticated(self):
        users = [
            User.objects.create(
                email="agent1@test.com", first_name="Agent", last_name="One"
            ),
            User.objects.create(
                email="agent2@test.com", first_name="Agent", last_name="Two"
            ),
            User.objects.create(
                email="agent3@test.com", first_name="Agent", last_name="Three"
            ),
        ]

        ProjectPermission.objects.create(user=users[0], project=self.project, role=2)
        room = Room.objects.create(queue=self.queue, user=users[0])
        room.is_active = False
        room.save()
        CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())

        ProjectPermission.objects.create(user=users[1], project=self.project, role=2)
        room = Room.objects.create(queue=self.queue, user=users[1])
        room.is_active = False
        room.save()
        CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())

        ProjectPermission.objects.create(user=users[2], project=self.project, role=2)

        response = self.get_agent_csat_metrics(self.project.uuid, {"page_size": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

        self.assertEqual(response.data["results"][0]["agent"]["name"], "Agent Two")
        self.assertEqual(
            response.data["results"][0]["agent"]["email"], "agent2@test.com"
        )
        self.assertEqual(response.data["results"][0]["rooms"], 1)
        self.assertEqual(response.data["results"][0]["reviews"], 1)
        self.assertEqual(response.data["results"][0]["avg_rating"], 5.0)

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


class BaseTestInternalDashboardViewSet(APITestCase):
    def list_custom_status_by_agent(
        self, project_uuid: str, query_params: dict = None
    ) -> Response:
        url = f"/v1/internal/dashboard/{project_uuid}/custom-status-by-agent/"

        return self.client.get(url, query_params)


class TestInternalDashboardViewSetAsAnonymousUser(BaseTestInternalDashboardViewSet):
    def test_list_custom_status_by_agent_when_unauthenticated(self):
        response = self.list_custom_status_by_agent(uuid.uuid4())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestInternalDashboardViewSetAsAuthenticatedUser(BaseTestInternalDashboardViewSet):
    def setUp(self):
        self.user = User.objects.create(
            email="internal@service.local",
            first_name="Internal",
            last_name="Service",
            is_active=True,
        )
        self.project = Project.objects.create(
            name="Test Project", timezone=pytz.timezone("America/Sao_Paulo")
        )
        self.status_types = CustomStatusType.objects.bulk_create(
            [
                CustomStatusType(
                    name=f"Test Status {i}",
                    project=self.project,
                )
                for i in range(2)
            ]
        )
        self.agents = [
            User.objects.create(
                email=f"agent{i}@test.com",
                first_name="Agent",
                last_name=f"Number {i}",
                is_active=True,
            )
            for i in range(2)
        ]
        ProjectPermission.objects.bulk_create(
            [
                ProjectPermission(
                    project=self.project,
                    user=agent,
                    role=ProjectPermission.ROLE_ATTENDANT,
                    status=ProjectPermission.STATUS_ONLINE,
                )
                for agent in self.agents
            ]
        )

        custom_status_to_create = []

        for agent in self.agents:
            for status_type in self.status_types:
                custom_status_to_create.append(
                    CustomStatus(
                        user=agent,
                        status_type=status_type,
                        is_active=False,
                        break_time=30,
                    )
                )

        CustomStatus.objects.bulk_create(custom_status_to_create)

        self.client.force_authenticate(user=self.user)

    def test_list_custom_status_by_agent_without_permission(self):
        response = self.list_custom_status_by_agent(self.project.uuid)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_list_custom_status_by_agent(self):
        response = self.list_custom_status_by_agent(
            self.project.uuid, {"ordering": "agent"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
