from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.api.utils import create_user_and_token
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.projects.usecases.close_org_rooms import (
    SAC_UNIFICADO_END_BY,
    CloseOrgRoomsUseCase,
)
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class CloseOrgRoomsUseCaseTests(APITestCase):
    def setUp(self):
        self.org_id = "org-sac-close"
        self.user = User.objects.create(email="closer@test.com")
        self.principal = Project.objects.create(name="Principal", org=self.org_id)
        self.secondary = Project.objects.create(name="Secondary", org=self.org_id)
        self.other_org = Project.objects.create(name="Other", org="org-other")

        self.principal_sector = self._sector(self.principal, "Principal sector")
        self.secondary_sector = self._sector(self.secondary, "Secondary sector")
        self.other_sector = self._sector(self.other_org, "Other sector")

        self.principal_queue = Queue.objects.create(
            name="Principal queue", sector=self.principal_sector
        )
        self.secondary_queue = Queue.objects.create(
            name="Secondary queue", sector=self.secondary_sector
        )
        self.other_queue = Queue.objects.create(
            name="Other queue", sector=self.other_sector
        )

    def _sector(self, project, name):
        return Sector.objects.create(
            name=name,
            project=project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )

    @patch("chats.apps.projects.usecases.close_org_rooms.BulkCloseService")
    def test_closes_active_rooms_of_every_project_in_the_org(self, mock_service):
        principal_room = Room.objects.create(queue=self.principal_queue)
        secondary_room = Room.objects.create(queue=self.secondary_queue)
        Room.objects.create(queue=self.principal_queue, is_active=False)
        Room.objects.create(queue=self.other_queue)

        CloseOrgRoomsUseCase().execute(self.principal, closed_by=self.user)

        mock_service.return_value.close.assert_called_once()
        kwargs = mock_service.return_value.close.call_args.kwargs
        closed_ids = set(kwargs["rooms"].values_list("pk", flat=True))
        self.assertEqual(closed_ids, {principal_room.pk, secondary_room.pk})
        self.assertEqual(kwargs["end_by"], SAC_UNIFICADO_END_BY)
        self.assertEqual(kwargs["closed_by"], self.user)

    @patch("chats.apps.projects.usecases.close_org_rooms.BulkCloseService")
    def test_does_nothing_when_the_org_has_no_active_rooms(self, mock_service):
        Room.objects.create(queue=self.principal_queue, is_active=False)

        result = CloseOrgRoomsUseCase().execute(self.principal, closed_by=self.user)

        self.assertIsNone(result)
        mock_service.return_value.close.assert_not_called()


class SetProjectAsPrincipalClosesRoomsTests(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("principalcloser")
        self.org_id = "org-set-principal"
        self.project = Project.objects.create(name="Main", org=self.org_id)
        self.other_project = Project.objects.create(name="Other", org=self.org_id)
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.url = reverse(
            "project-set-project-as-principal", kwargs={"uuid": str(self.project.uuid)}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch("chats.apps.api.v1.projects.viewsets.CloseOrgRoomsUseCase")
    def test_set_as_principal_closes_org_rooms(self, mock_usecase):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertTrue(self.project.config.get("its_principal"))
        mock_usecase.return_value.execute.assert_called_once_with(
            self.project, closed_by=self.user
        )
