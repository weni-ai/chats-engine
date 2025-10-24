import uuid
from unittest.mock import patch

from django.utils import timezone
from django.db.models import Avg, Count
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response
from rest_framework.request import Request

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
        ]

        for user in users:
            ProjectPermission.objects.create(user=user, project=self.project, role=2)
            room = Room.objects.create(queue=self.queue, user=user)
            room.is_active = False
            room.save()
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())

        response = self.get_agent_csat_metrics(self.project.uuid, {"page_size": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
