from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.projects.usecases.status_service import InServiceStatusService

User = get_user_model()


class InServiceStatusServiceTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Status Project")
        self.user = User.objects.create_user(email="agent@test.com", password="pw")

    def test_room_assigned_returns_when_user_is_missing(self):
        self.assertIsNone(InServiceStatusService.room_assigned(None, self.project))

    def test_room_assigned_returns_when_project_is_missing(self):
        self.assertIsNone(InServiceStatusService.room_assigned(self.user, None))

    def test_room_assigned_returns_when_permission_is_missing(self):
        with patch.object(
            InServiceStatusService, "get_or_create_status_type"
        ) as mock_type:
            self.assertIsNone(
                InServiceStatusService.room_assigned(self.user, self.project)
            )
        mock_type.assert_not_called()

    def test_room_closed_returns_when_user_or_project_is_missing(self):
        self.assertIsNone(InServiceStatusService.room_closed(None, self.project))
        self.assertIsNone(InServiceStatusService.room_closed(self.user, None))

    def test_room_assigned_does_not_create_status_when_agent_is_offline(self):
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status="OFFLINE",
        )

        InServiceStatusService.room_assigned(self.user, self.project)

        status_type = InServiceStatusService.get_or_create_status_type(self.project)
        from chats.apps.projects.models.models import CustomStatus

        self.assertFalse(
            CustomStatus.objects.filter(
                user=self.user, project=self.project, status_type=status_type
            ).exists()
        )
