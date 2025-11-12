import uuid
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response


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
