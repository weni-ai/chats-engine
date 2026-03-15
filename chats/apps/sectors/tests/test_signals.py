from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization

User = get_user_model()


class SectorAuthorizationSignalTestCase(TestCase):
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
        self.sector_auth = SectorAuthorization.objects.create(
            permission=self.permission,
            sector=self.sector,
            role=SectorAuthorization.ROLE_MANAGER,
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=self.permission,
            role=QueueAuthorization.ROLE_AGENT,
        )

    @patch("chats.apps.sectors.signals.requeue_agent_rooms_task")
    def test_requeue_triggered_on_sector_auth_delete(self, mock_task):
        Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=True
        )

        self.sector_auth.delete()

        mock_task.delay.assert_called_once()
        room_uuids = mock_task.delay.call_args[0][0]
        self.assertEqual(len(room_uuids), 1)

    @patch("chats.apps.sectors.signals.requeue_agent_rooms_task")
    def test_requeue_not_triggered_when_no_active_rooms(self, mock_task):
        Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.agent, is_active=False
        )

        self.sector_auth.delete()

        mock_task.delay.assert_not_called()

    @patch("chats.apps.sectors.signals.requeue_agent_rooms_task")
    def test_requeue_not_triggered_when_no_rooms(self, mock_task):
        self.sector_auth.delete()
        mock_task.delay.assert_not_called()
