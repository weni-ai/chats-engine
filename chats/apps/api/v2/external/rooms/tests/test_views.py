from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response


class BaseTestExternalRoomMetrics(APITestCase):
    def list_rooms_metrics(self, filters: dict = {}) -> Response:
        url = reverse("external_rooms_metrics_v2-list")

        return self.client.get(url, filters)


class TestExternalRoomMetricsAsAnonymousUser(BaseTestExternalRoomMetrics):
    def test_list_rooms_metrics_as_anonymous_user(self):
        response = self.list_rooms_metrics()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
