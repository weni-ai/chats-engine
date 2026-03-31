from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.projects.models.models import Project, ProjectPermission

User = get_user_model()


class RequeueRoomsOnPermissionDeleteTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Signal Test Project")
        self.agent = User.objects.create_user(email="agent@test.com", password="pw")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_requeue_triggered_on_permission_delete(self, mock_task):
        self.permission.delete()
        mock_task.delay.assert_called_once_with(
            str(self.agent.pk),
            str(self.project.pk),
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_requeue_not_triggered_when_permission_already_deleted(self, mock_task):
        self.permission.is_deleted = True
        self.permission.save()
        mock_task.reset_mock()
        self.permission.save()
        mock_task.delay.assert_not_called()

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_requeue_not_triggered_on_create(self, mock_task):
        new_agent = User.objects.create_user(email="new@test.com", password="pw")
        ProjectPermission.objects.create(
            project=self.project,
            user=new_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        mock_task.delay.assert_not_called()
