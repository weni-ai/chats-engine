from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock

from chats.apps.rooms.models import Room
from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue


class RoomModelTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector", 
            project=self.project,
            rooms_limit=5,  
            work_start="08:00:00",
            work_end="17:00:00"
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        
        self.user1 = User.objects.create(
            email="agent1@example.com",
            first_name="Agent",
            last_name="One"
        )
        
        self.user2 = User.objects.create(
            email="agent2@example.com",
            first_name="Agent",
            last_name="Two"
        )

    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker.update_room_count')
    def test_update_agent_service_status_new_room_with_user(self, mock_update_count):
        """Testa se _update_agent_service_status atualiza corretamente para uma sala nova com usuário"""
        room = Room(
            user=self.user1,
            queue=self.queue,
            is_active=True
        )
        
        room._state.adding = True
        
        room._update_agent_service_status(is_new=True)
        
        mock_update_count.assert_called_once_with(self.user1, self.project, "assigned")

    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker.update_room_count')
    def test_update_agent_service_status_assign_user(self, mock_update_count):
        """Testa se _update_agent_service_status atualiza corretamente quando um usuário é atribuído"""
        room = Room.objects.create(
            queue=self.queue,
            is_active=True
        )
        
        room.tracker = MagicMock()
        room.tracker.previous.return_value = None
        
        room.user = self.user1
        
        room._update_agent_service_status(is_new=False)
        
        mock_update_count.assert_called_once_with(self.user1, self.project, "assigned")

    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker.update_room_count')
    def test_update_agent_service_status_transfer_between_users(self, mock_update_count):
        """Testa se _update_agent_service_status atualiza corretamente quando um usuário é alterado"""
        room = Room.objects.create(
            user=self.user1,
            queue=self.queue,
            is_active=True
        )
        
        mock_update_count.reset_mock()
        
        room.tracker = MagicMock()
        room.tracker.previous.return_value = self.user1
        
        room.user = self.user2
        
        room._update_agent_service_status(is_new=False)
        
        calls = mock_update_count.call_args_list
        self.assertEqual(len(calls), 2)
        mock_update_count.assert_any_call(self.user1, self.project, "closed")
        mock_update_count.assert_any_call(self.user2, self.project, "assigned")

    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker.update_room_count')
    def test_update_agent_service_status_transfer_to_queue(self, mock_update_count):
        """Testa se _update_agent_service_status atualiza corretamente quando um usuário é removido"""
        room = Room.objects.create(
            user=self.user1,
            queue=self.queue,
            is_active=True
        )
        
        mock_update_count.reset_mock()
        
        room.tracker = MagicMock()
        room.tracker.previous.return_value = self.user1
        
        room.user = None
        
        room._update_agent_service_status(is_new=False)
        
        mock_update_count.assert_called_once_with(self.user1, self.project, "closed")

    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker.update_room_count')
    def test_update_agent_service_status_close_room(self, mock_update_count):
        """Testa se _update_agent_service_status atualiza corretamente quando uma sala é fechada"""
        room = Room.objects.create(
            user=self.user1,
            queue=self.queue,
            is_active=True
        )
        
        mock_update_count.reset_mock()
        
        room.tracker = MagicMock()
        room.tracker.previous.side_effect = lambda field: True if field == 'is_active' else self.user1
        
        room.is_active = False
        
        room._update_agent_service_status(is_new=False)
        
        mock_update_count.assert_called_once_with(self.user1, self.project, "closed")

    @patch('chats.apps.rooms.models.Room._update_agent_service_status')
    def test_save_method_calls_update_agent_service_status(self, mock_update):
        """Testa se o método save chama _update_agent_service_status"""
        room = Room(
            user=self.user1,
            queue=self.queue,
            is_active=True
        )
        room.save()
        
        mock_update.assert_called_once_with(True)
        
        mock_update.reset_mock()
        room.user = self.user2
        room.save()
        
        mock_update.assert_called_once_with(False)