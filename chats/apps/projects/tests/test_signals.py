from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class ProjectPermissionSignalTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Signal Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Client")
        self.agent = User.objects.create_user(email="agent@test.com", password="pw")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=self.permission,
            role=QueueAuthorization.ROLE_AGENT,
        )

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_requeue_triggered_on_permission_delete(self, mock_task):
        Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )

        self.permission.delete()

        mock_task.delay.assert_called_once()
        room_uuids = mock_task.delay.call_args[0][0]
        self.assertEqual(len(room_uuids), 1)

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_requeue_not_triggered_when_no_active_rooms(self, mock_task):
        Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=False
        )

        self.permission.delete()

        mock_task.delay.assert_not_called()

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_requeue_not_triggered_when_no_rooms(self, mock_task):
        self.permission.delete()
        mock_task.delay.assert_not_called()

    @patch("chats.apps.projects.models.signals.requeue_agent_rooms_task")
    def test_only_rooms_in_deleted_project_are_requeued(self, mock_task):
        other_project = Project.objects.create(name="Other Project")
        other_sector = Sector.objects.create(
            name="Other Sector",
            project=other_project,
            rooms_limit=5,
            work_start="00:00",
            work_end="23:59",
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)

        room_in_project = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )
        Room.objects.create(
            queue=other_queue, contact=self.contact, user=self.agent, is_active=True
        )

        self.permission.delete()

        mock_task.delay.assert_called_once()
        room_uuids = mock_task.delay.call_args[0][0]
        self.assertEqual(room_uuids, [str(room_in_project.uuid)])
