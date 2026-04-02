from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector, SectorAuthorization

User = get_user_model()


class HandlePermissionSoftDeleteTestCase(TestCase):
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
            str(self.agent.email),
            str(self.project.uuid),
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


class RemoveAuthorizationsOnPermissionSoftDeleteTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Signal Test Project")
        self.agent = User.objects.create_user(email="agent@test.com", password="pw")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )
        self.sector_auth = SectorAuthorization.objects.create(
            permission=self.permission,
            sector=self.sector,
        )
        self.queue_auth = QueueAuthorization.objects.create(
            permission=self.permission,
            queue=self.queue,
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_authorizations_deleted_on_permission_soft_delete(self, mock_task):
        self.permission.delete()

        self.assertFalse(
            SectorAuthorization.objects.filter(pk=self.sector_auth.pk).exists()
        )
        self.assertFalse(
            QueueAuthorization.objects.filter(pk=self.queue_auth.pk).exists()
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_authorizations_not_deleted_on_regular_save(self, mock_task):
        self.permission.role = ProjectPermission.ROLE_ADMIN
        self.permission.save()

        self.assertTrue(
            SectorAuthorization.objects.filter(pk=self.sector_auth.pk).exists()
        )
        self.assertTrue(
            QueueAuthorization.objects.filter(pk=self.queue_auth.pk).exists()
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_authorizations_not_deleted_on_create(self, mock_task):
        new_agent = User.objects.create_user(email="new@test.com", password="pw")
        new_permission = ProjectPermission.objects.create(
            project=self.project,
            user=new_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        SectorAuthorization.objects.create(
            permission=new_permission,
            sector=self.sector,
        )
        QueueAuthorization.objects.create(
            permission=new_permission,
            queue=self.queue,
        )

        self.assertEqual(
            SectorAuthorization.objects.filter(permission=new_permission).count(), 1
        )
        self.assertEqual(
            QueueAuthorization.objects.filter(permission=new_permission).count(), 1
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_no_error_when_permission_has_no_authorizations(self, mock_task):
        self.sector_auth.delete()
        self.queue_auth.delete()

        self.permission.delete()

        self.assertFalse(
            SectorAuthorization.objects.filter(permission=self.permission).exists()
        )
        self.assertFalse(
            QueueAuthorization.objects.filter(permission=self.permission).exists()
        )


class AuthorizationManagerFilterTestCase(TestCase):
    """Tests that the custom managers on SectorAuthorization and
    QueueAuthorization exclude rows whose permission has been soft-deleted."""

    def setUp(self):
        self.project = Project.objects.create(name="Manager Test Project")
        self.agent = User.objects.create_user(email="mgr@test.com", password="pw")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )
        self.sector_auth = SectorAuthorization.objects.create(
            permission=self.permission,
            sector=self.sector,
        )
        self.queue_auth = QueueAuthorization.objects.create(
            permission=self.permission,
            queue=self.queue,
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_sector_auth_visible_when_permission_active(self, mock_task):
        self.assertTrue(
            SectorAuthorization.objects.filter(pk=self.sector_auth.pk).exists()
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_queue_auth_visible_when_permission_active(self, mock_task):
        self.assertTrue(
            QueueAuthorization.objects.filter(pk=self.queue_auth.pk).exists()
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_sector_auth_hidden_when_permission_soft_deleted(self, mock_task):
        self.permission.delete()
        self.assertFalse(
            SectorAuthorization.objects.filter(pk=self.sector_auth.pk).exists()
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_queue_auth_hidden_when_permission_soft_deleted(self, mock_task):
        self.permission.delete()
        self.assertFalse(
            QueueAuthorization.objects.filter(pk=self.queue_auth.pk).exists()
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_other_agents_authorizations_unaffected(self, mock_task):
        other_agent = User.objects.create_user(email="other@test.com", password="pw")
        other_perm = ProjectPermission.objects.create(
            project=self.project,
            user=other_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        other_sector_auth = SectorAuthorization.objects.create(
            permission=other_perm,
            sector=self.sector,
        )
        other_queue_auth = QueueAuthorization.objects.create(
            permission=other_perm,
            queue=self.queue,
        )

        self.permission.delete()

        self.assertTrue(
            SectorAuthorization.objects.filter(pk=other_sector_auth.pk).exists()
        )
        self.assertTrue(
            QueueAuthorization.objects.filter(pk=other_queue_auth.pk).exists()
        )
