import uuid
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


class RoomsCountByAgentViewTests(APITestCase):
    def setUp(self):
        flag_patcher = patch(
            "chats.apps.api.v1.rooms.viewsets.is_feature_active",
            return_value=True,
        )
        self._mock_feature_flag = flag_patcher.start()
        self.addCleanup(flag_patcher.stop)

        self.url = reverse("rooms-count-by-agent")
        self.project = Project.objects.create(name="Test Project")
        sector = Sector.objects.create(
            name="Support",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        Queue.objects.create(name="Support Queue", sector=sector)
        self.admin = User.objects.create_user(
            email="admin@test.com", first_name="Admin"
        )
        ProjectPermission.objects.create(
            user=self.admin,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.client.force_authenticate(user=self.admin)

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url, {"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_project_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_disabled_feature_flag_returns_404(self):
        self._mock_feature_flag.return_value = False
        response = self.client.get(self.url, {"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unknown_project_returns_403(self):
        response = self.client.get(self.url, {"project": str(uuid.uuid4())})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_receives_own_row_with_email_as_uuid(self):
        response = self.client.get(self.url, {"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "agents": [
                    {
                        "name": "Admin",
                        "uuid": "admin@test.com",
                        "rooms_in_awaiting": 0,
                        "rooms_in_progress": 0,
                    }
                ]
            },
        )
