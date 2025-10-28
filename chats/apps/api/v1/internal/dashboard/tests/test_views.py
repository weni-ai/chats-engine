import uuid

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector
from chats.apps.rooms.models import Room
from chats.apps.csat.models import CSATSurvey


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
