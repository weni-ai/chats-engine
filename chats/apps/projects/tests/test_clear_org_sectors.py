from unittest.mock import Mock, patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.projects.usecases.clear_org_sectors import (
    ClearOrgSectorsError,
    ClearOrgSectorsUseCase,
)
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class ClearOrgSectorsUseCaseTests(APITestCase):
    def setUp(self):
        self.org_id = "org-sac-clear"
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

    @patch("chats.apps.projects.usecases.clear_org_sectors.BulkCloseService")
    def test_deletes_sectors_and_queues_of_the_org(self, mock_close):
        active_room = Room.objects.create(queue=self.principal_queue)

        ClearOrgSectorsUseCase().execute(self.principal, user_email="agent@test.com")

        closed_ids = set(
            mock_close.return_value.close.call_args.kwargs["rooms"].values_list(
                "pk", flat=True
            )
        )
        self.assertEqual(closed_ids, {active_room.pk})

        self.principal_sector.refresh_from_db()
        self.secondary_sector.refresh_from_db()
        self.other_sector.refresh_from_db()
        self.principal_queue.refresh_from_db()
        self.secondary_queue.refresh_from_db()
        self.other_queue.refresh_from_db()

        self.assertTrue(self.principal_sector.is_deleted)
        self.assertTrue(self.secondary_sector.is_deleted)
        self.assertFalse(self.other_sector.is_deleted)
        self.assertTrue(self.principal_queue.is_deleted)
        self.assertTrue(self.secondary_queue.is_deleted)
        self.assertFalse(self.other_queue.is_deleted)

    @patch("chats.apps.projects.usecases.clear_org_sectors.BulkCloseService")
    def test_does_nothing_when_the_org_has_no_sectors(self, mock_close):
        empty = Project.objects.create(name="Empty", org="org-empty")

        ClearOrgSectorsUseCase().execute(empty)

        mock_close.return_value.close.assert_not_called()

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.projects.usecases.clear_org_sectors.BulkCloseService")
    @patch("chats.apps.projects.usecases.clear_org_sectors.FlowRESTClient")
    def test_destroys_sector_and_queue_on_flows_before_local_delete(
        self, mock_client, _mock_close
    ):
        ok = Mock(status_code=status.HTTP_204_NO_CONTENT)
        mock_client.return_value.destroy_queue.return_value = ok
        mock_client.return_value.destroy_sector.return_value = ok
        self.principal_sector.secondary_project = {"uuid": "secondary-uuid"}
        self.principal_sector.save()

        ClearOrgSectorsUseCase().execute(self.principal, user_email="agent@test.com")

        mock_client.return_value.destroy_queue.assert_any_call(
            uuid=str(self.principal_queue.uuid),
            sector_uuid=str(self.principal_sector.uuid),
            project_uuid="secondary-uuid",
        )
        mock_client.return_value.destroy_sector.assert_any_call(
            sector_uuid=str(self.principal_sector.uuid),
            user_email="agent@test.com",
        )
        self.principal_sector.refresh_from_db()
        self.assertTrue(self.principal_sector.is_deleted)

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.projects.usecases.clear_org_sectors.BulkCloseService")
    @patch("chats.apps.projects.usecases.clear_org_sectors.FlowRESTClient")
    def test_keeps_sector_when_flows_delete_fails(self, mock_client, _mock_close):
        mock_client.return_value.destroy_queue.return_value = Mock(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        with self.assertRaises(ClearOrgSectorsError):
            ClearOrgSectorsUseCase().execute(self.principal)

        self.principal_sector.refresh_from_db()
        self.assertFalse(self.principal_sector.is_deleted)


class SetProjectAsPrincipalClearsSectorsTests(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("principalclear")
        self.project = Project.objects.create(name="Main", org="org-set-clear")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.url = reverse(
            "project-set-project-as-principal", kwargs={"uuid": str(self.project.uuid)}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch("chats.apps.api.v1.projects.viewsets.ClearOrgSectorsUseCase")
    def test_set_as_principal_clears_org_sectors(self, mock_usecase):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_usecase.return_value.execute.assert_called_once_with(
            self.project, user_email=self.user.email
        )
