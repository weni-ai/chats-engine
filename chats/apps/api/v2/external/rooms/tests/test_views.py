from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project


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

        self.token = str(self.project.external_token.uuid)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_can_list_rooms_metrics(self):
        response = self.list_rooms_metrics()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
