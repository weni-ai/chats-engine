import uuid
import pytz

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import (
    CustomStatus,
    CustomStatusType,
    Project,
    ProjectPermission,
)
from chats.apps.accounts.tests.decorators import with_internal_auth


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

        response = self.list_custom_status_by_agent(self.project.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
