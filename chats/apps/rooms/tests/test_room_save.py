from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class RoomSaveTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector", project=self.project, rooms_limit=10
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create_user(
            email="agent@test.com", first_name="Agent", last_name="Test"
        )
        self.contact = Contact.objects.create(
            name="Test Contact", email="contact@test.com"
        )

    def test_save_new_room_sets_added_to_queue_at(self):
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        self.assertIsNotNone(room.added_to_queue_at)

    def test_save_new_room_with_user_sets_user_assigned_at(self):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user
        )
        self.assertIsNotNone(room.user_assigned_at)

    def test_save_new_room_with_user_sets_first_user_assigned_at(self):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user
        )
        self.assertIsNotNone(room.first_user_assigned_at)

    def test_save_room_user_change_updates_user_assigned_at(self):
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        initial_assigned_at = room.user_assigned_at

        new_user = User.objects.create_user(
            email="agent2@test.com", first_name="Agent2", last_name="Test"
        )
        room.user = new_user
        room.save()

        self.assertIsNotNone(room.user_assigned_at)
        self.assertNotEqual(room.user_assigned_at, initial_assigned_at)

    def test_save_room_user_removed_updates_added_to_queue_at(self):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user
        )
        initial_added_at = room.added_to_queue_at

        room.user = None
        room.save()

        self.assertIsNotNone(room.added_to_queue_at)
        self.assertNotEqual(room.added_to_queue_at, initial_added_at)

    @patch("chats.apps.rooms.models.InServiceStatusService")
    def test_save_new_room_with_user_calls_room_assigned(self, mock_service):
        Room.objects.create(queue=self.queue, contact=self.contact, user=self.user)

        mock_service.room_assigned.assert_called_with(self.user, self.project)

    @patch("chats.apps.rooms.models.InServiceStatusService")
    def test_save_room_user_added_calls_room_assigned(self, mock_service):
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        mock_service.reset_mock()

        room.user = self.user
        room.save()

        mock_service.room_assigned.assert_called_once_with(self.user, self.project)

    @patch("chats.apps.rooms.models.InServiceStatusService")
    def test_save_room_user_changed_calls_both_services(self, mock_service):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user
        )
        mock_service.reset_mock()

        new_user = User.objects.create_user(
            email="agent2@test.com", first_name="Agent2", last_name="Test"
        )
        room.user = new_user
        room.save()

        mock_service.room_closed.assert_called_once_with(self.user, self.project)
        mock_service.room_assigned.assert_called_once_with(new_user, self.project)

    @patch("chats.apps.rooms.models.InServiceStatusService")
    def test_save_room_user_removed_calls_room_closed(self, mock_service):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user
        )
        mock_service.reset_mock()

        room.user = None
        room.save()

        mock_service.room_closed.assert_called_once_with(self.user, self.project)


class UpdateAgentServiceStatusTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector", project=self.project, rooms_limit=10
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.user = User.objects.create_user(
            email="agent@test.com", first_name="Agent", last_name="Test"
        )
        self.contact = Contact.objects.create(
            name="Test Contact", email="contact@test.com"
        )

    @patch("chats.apps.rooms.models.InServiceStatusService")
    def test_update_agent_service_status_no_project(self, mock_service):
        room = Room(queue=None, contact=self.contact)
        room._original_user = None
        room._update_agent_service_status(is_new=True)

        mock_service.room_assigned.assert_not_called()
        mock_service.room_closed.assert_not_called()

    @patch("chats.apps.rooms.models.InServiceStatusService")
    def test_update_agent_service_status_new_room_with_user(self, mock_service):
        Room.objects.create(queue=self.queue, contact=self.contact, user=self.user)

        mock_service.room_assigned.assert_called_with(self.user, self.project)

    @patch("chats.apps.rooms.models.InServiceStatusService")
    def test_update_agent_service_status_old_user_none_new_user_assigned(
        self, mock_service
    ):
        room = Room.objects.create(queue=self.queue, contact=self.contact)
        mock_service.reset_mock()

        room._original_user = None
        room.user = self.user
        room._update_agent_service_status(is_new=False)

        mock_service.room_assigned.assert_called_once_with(self.user, self.project)

    @patch("chats.apps.rooms.models.InServiceStatusService")
    def test_update_agent_service_status_user_changed(self, mock_service):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user
        )
        mock_service.reset_mock()

        new_user = User.objects.create_user(
            email="agent2@test.com", first_name="Agent2", last_name="Test"
        )
        room._original_user = self.user
        room.user = new_user
        room._update_agent_service_status(is_new=False)

        mock_service.room_closed.assert_called_once_with(self.user, self.project)
        mock_service.room_assigned.assert_called_once_with(new_user, self.project)

    @patch("chats.apps.rooms.models.InServiceStatusService")
    def test_update_agent_service_status_user_removed(self, mock_service):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user
        )
        mock_service.reset_mock()

        room._original_user = self.user
        room.user = None
        room._update_agent_service_status(is_new=False)

        mock_service.room_closed.assert_called_once_with(self.user, self.project)

    @patch("chats.apps.rooms.models.InServiceStatusService")
    def test_update_agent_service_status_same_user_no_action(self, mock_service):
        room = Room.objects.create(
            queue=self.queue, contact=self.contact, user=self.user
        )
        mock_service.reset_mock()

        room._original_user = self.user
        room._update_agent_service_status(is_new=False)

        mock_service.room_closed.assert_not_called()
        mock_service.room_assigned.assert_not_called()
