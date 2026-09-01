from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission, TemplateType
from chats.apps.projects.usecases.sector_setup_handler import (
    SectorSetupHandlerUseCase,
)
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector, SectorAuthorization


class TestSectorSetupHandlerUseCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Setup Test Project")
        self.user = User.objects.create(email="creator@test.com")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

    def _make_template_type(self, setup):
        return TemplateType.objects.create(name="TT", setup=setup)

    @patch(
        "chats.apps.projects.usecases.sector_setup_handler.FlowsEDAClient.request_ticketer"
    )
    def test_setup_skips_sectors_without_queues(self, mock_request_ticketer):
        template_type = self._make_template_type(
            setup={
                "sectors": [
                    {
                        "name": "Empty Sector",
                        "rooms_limit": 1,
                        "work_start": "08:00",
                        "work_end": "18:00",
                    }
                ]
            }
        )

        SectorSetupHandlerUseCase().setup_sectors_in_project(
            project=self.project,
            template_type=template_type,
            creator_permission=self.permission,
        )

        self.assertFalse(Sector.objects.filter(project=self.project).exists())
        mock_request_ticketer.assert_not_called()

    @patch(
        "chats.apps.projects.usecases.sector_setup_handler.FlowsEDAClient.request_ticketer"
    )
    def test_setup_skips_sectors_that_already_exist(self, mock_request_ticketer):
        Sector.objects.create(
            name="Existing Sector",
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )
        template_type = self._make_template_type(
            setup={
                "sectors": [
                    {
                        "name": "Existing Sector",
                        "rooms_limit": 5,
                        "work_start": "08:00",
                        "work_end": "18:00",
                        "queues": [{"name": "Q1"}],
                    }
                ]
            }
        )

        SectorSetupHandlerUseCase().setup_sectors_in_project(
            project=self.project,
            template_type=template_type,
            creator_permission=self.permission,
        )

        # No authorizations or queues added; EDA not called
        self.assertFalse(SectorAuthorization.objects.exists())
        self.assertFalse(Queue.objects.exists())
        mock_request_ticketer.assert_not_called()

    @patch(
        "chats.apps.projects.usecases.sector_setup_handler.FlowsEDAClient.request_ticketer"
    )
    def test_setup_creates_sectors_queues_and_authorizations(
        self, mock_request_ticketer
    ):
        template_type = self._make_template_type(
            setup={
                "sectors": [
                    {
                        "name": "Setup Sector",
                        "rooms_limit": 2,
                        "work_start": "09:00",
                        "work_end": "17:00",
                        "queues": [{"name": "Q1"}, {"name": "Q2"}],
                    }
                ]
            }
        )

        SectorSetupHandlerUseCase().setup_sectors_in_project(
            project=self.project,
            template_type=template_type,
            creator_permission=self.permission,
        )

        sector = Sector.objects.get(name="Setup Sector", project=self.project)
        self.assertEqual(sector.rooms_limit, 2)
        self.assertEqual(Queue.objects.filter(sector=sector).count(), 2)
        self.assertTrue(
            SectorAuthorization.objects.filter(
                permission=self.permission, sector=sector, role=1
            ).exists()
        )
        self.assertEqual(
            QueueAuthorization.objects.filter(
                permission=self.permission, role=1
            ).count(),
            2,
        )

        mock_request_ticketer.assert_called_once()
        content = mock_request_ticketer.call_args.kwargs["content"]
        self.assertEqual(content["name"], "Setup Sector")
        self.assertEqual(content["user_email"], self.user.email)
        self.assertEqual({q["name"] for q in content["queues"]}, {"Q1", "Q2"})
