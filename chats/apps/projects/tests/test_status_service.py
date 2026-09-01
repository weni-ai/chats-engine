from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import CustomStatus, CustomStatusType
from chats.apps.projects.usecases.status_service import (
    InServiceStatusService,
    InServiceStatusTracker,
)
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class _BaseStatusServiceTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Status Project")
        self.user = User.objects.create(email="status-agent@test.com")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
            status="ONLINE",
        )
        self.sector = Sector.objects.create(
            name="Status Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Status Queue", sector=self.sector)


class TestGetOrCreateStatusType(_BaseStatusServiceTestCase):
    def test_creates_status_type_once(self):
        st1 = InServiceStatusService.get_or_create_status_type(self.project)
        st2 = InServiceStatusService.get_or_create_status_type(self.project)
        self.assertEqual(st1.pk, st2.pk)
        self.assertEqual(st1.name, "In-Service")
        self.assertEqual(st1.project, self.project)


class TestHasPriorityStatus(_BaseStatusServiceTestCase):
    def test_returns_false_when_no_status(self):
        self.assertFalse(
            InServiceStatusService.has_priority_status(self.user, self.project)
        )

    def test_returns_true_when_other_active_status(self):
        other = CustomStatusType.objects.create(
            name="Lunch", project=self.project, is_deleted=False, config={}
        )
        CustomStatus.objects.create(
            user=self.user,
            status_type=other,
            is_active=True,
            project=self.project,
            break_time=0,
        )
        self.assertTrue(
            InServiceStatusService.has_priority_status(self.user, self.project)
        )


class TestRoomAssigned(_BaseStatusServiceTestCase):
    @patch("chats.apps.projects.tasks.log_agent_status_change.delay")
    def test_short_circuits_when_user_or_project_missing(self, mock_log):
        InServiceStatusService.room_assigned(None, self.project)
        InServiceStatusService.room_assigned(self.user, None)
        mock_log.assert_not_called()

    @patch("chats.apps.projects.tasks.log_agent_status_change.delay")
    def test_returns_early_when_no_permission(self, mock_log):
        agent_no_perm = User.objects.create(email="no-perm@test.com")
        InServiceStatusService.room_assigned(agent_no_perm, self.project)
        mock_log.assert_not_called()

    @patch("chats.apps.projects.tasks.log_agent_status_change.delay")
    def test_creates_in_service_status_when_first_room(self, mock_log):
        Room.objects.create(queue=self.queue, user=self.user)

        InServiceStatusService.room_assigned(self.user, self.project)

        status_type = CustomStatusType.objects.get(
            name="In-Service", project=self.project
        )
        self.assertTrue(
            CustomStatus.objects.filter(
                user=self.user,
                status_type=status_type,
                is_active=True,
                project=self.project,
            ).exists()
        )
        mock_log.assert_called_once()

    @patch("chats.apps.projects.tasks.log_agent_status_change.delay")
    def test_does_not_create_status_when_user_offline(self, mock_log):
        self.permission.status = "OFFLINE"
        self.permission.save()
        Room.objects.create(queue=self.queue, user=self.user)

        InServiceStatusService.room_assigned(self.user, self.project)

        self.assertFalse(
            CustomStatus.objects.filter(
                user=self.user, is_active=True, project=self.project
            ).exists()
        )
        mock_log.assert_not_called()

    @patch("chats.apps.projects.tasks.log_agent_status_change.delay")
    def test_does_not_create_when_priority_status_active(self, mock_log):
        other = CustomStatusType.objects.create(
            name="Lunch", project=self.project, is_deleted=False, config={}
        )
        CustomStatus.objects.create(
            user=self.user,
            status_type=other,
            is_active=True,
            project=self.project,
            break_time=0,
        )
        Room.objects.create(queue=self.queue, user=self.user)

        InServiceStatusService.room_assigned(self.user, self.project)

        in_service_type = CustomStatusType.objects.get(
            name="In-Service", project=self.project
        )
        self.assertFalse(
            CustomStatus.objects.filter(
                user=self.user, status_type=in_service_type, is_active=True
            ).exists()
        )
        mock_log.assert_not_called()


class TestRoomClosed(_BaseStatusServiceTestCase):
    @patch("chats.apps.projects.tasks.log_agent_status_change.delay")
    def test_short_circuits_when_args_missing(self, mock_log):
        InServiceStatusService.room_closed(None, self.project)
        InServiceStatusService.room_closed(self.user, None)
        mock_log.assert_not_called()

    @patch("chats.apps.projects.tasks.log_agent_status_change.delay")
    def test_closes_status_when_no_more_active_rooms(self, mock_log):
        status_type = InServiceStatusService.get_or_create_status_type(self.project)
        status = CustomStatus.objects.create(
            user=self.user,
            status_type=status_type,
            is_active=True,
            project=self.project,
            break_time=0,
        )

        InServiceStatusService.room_closed(self.user, self.project)

        status.refresh_from_db()
        self.assertFalse(status.is_active)
        self.assertGreaterEqual(status.break_time, 0)
        mock_log.assert_called_once()

    @patch("chats.apps.projects.tasks.log_agent_status_change.delay")
    def test_no_status_to_close_logs_warning(self, mock_log):
        InServiceStatusService.get_or_create_status_type(self.project)
        InServiceStatusService.room_closed(self.user, self.project)
        mock_log.assert_not_called()

    @patch("chats.apps.projects.tasks.log_agent_status_change.delay")
    def test_does_nothing_when_active_rooms_remain(self, mock_log):
        status_type = InServiceStatusService.get_or_create_status_type(self.project)
        CustomStatus.objects.create(
            user=self.user,
            status_type=status_type,
            is_active=True,
            project=self.project,
            break_time=0,
        )
        Room.objects.create(queue=self.queue, user=self.user)

        InServiceStatusService.room_closed(self.user, self.project)

        # status remains active
        self.assertTrue(
            CustomStatus.objects.filter(
                user=self.user, status_type=status_type, is_active=True
            ).exists()
        )
        mock_log.assert_not_called()


class TestSyncAgentStatus(_BaseStatusServiceTestCase):
    def test_returns_when_user_does_not_exist(self):
        # Should not raise
        InServiceStatusService.sync_agent_status(999999, self.project)

    def test_returns_when_project_does_not_exist(self):
        import uuid

        InServiceStatusService.sync_agent_status(self.user, str(uuid.uuid4()))

    def test_creates_status_when_rooms_active_and_no_status(self):
        Room.objects.create(queue=self.queue, user=self.user)
        # Remove the In-Service status auto-created by Room.save() so we exercise
        # the create-branch inside sync_agent_status itself.
        CustomStatus.objects.all().delete()

        InServiceStatusService.sync_agent_status(self.user, self.project)

        st = CustomStatusType.objects.get(name="In-Service", project=self.project)
        self.assertTrue(
            CustomStatus.objects.filter(
                user=self.user, status_type=st, is_active=True
            ).exists()
        )

    def test_closes_status_when_no_rooms_and_status_active(self):
        st = InServiceStatusService.get_or_create_status_type(self.project)
        status = CustomStatus.objects.create(
            user=self.user,
            status_type=st,
            is_active=True,
            project=self.project,
            break_time=0,
        )

        InServiceStatusService.sync_agent_status(self.user, self.project)

        status.refresh_from_db()
        self.assertFalse(status.is_active)

    def test_does_nothing_when_priority_status_active(self):
        other = CustomStatusType.objects.create(
            name="Pause", project=self.project, is_deleted=False, config={}
        )
        CustomStatus.objects.create(
            user=self.user,
            status_type=other,
            is_active=True,
            project=self.project,
            break_time=0,
        )
        Room.objects.create(queue=self.queue, user=self.user)

        InServiceStatusService.sync_agent_status(self.user, self.project)

        in_service_type = InServiceStatusService.get_or_create_status_type(self.project)
        self.assertFalse(
            CustomStatus.objects.filter(
                user=self.user, status_type=in_service_type, is_active=True
            ).exists()
        )


class TestScheduleSyncForAllAgents(_BaseStatusServiceTestCase):
    @patch.object(InServiceStatusService, "sync_agent_status")
    def test_dispatches_sync_for_each_active_agent(self, mock_sync):
        Room.objects.create(queue=self.queue, user=self.user)
        other_user = User.objects.create(email="other@test.com")
        Room.objects.create(queue=self.queue, user=other_user)

        InServiceStatusService.schedule_sync_for_all_agents()

        self.assertEqual(mock_sync.call_count, 2)

    @patch.object(InServiceStatusService, "sync_agent_status")
    def test_continues_when_one_sync_raises(self, mock_sync):
        mock_sync.side_effect = Exception("boom")
        Room.objects.create(queue=self.queue, user=self.user)

        # Should not raise
        InServiceStatusService.schedule_sync_for_all_agents()

        mock_sync.assert_called()


class TestInServiceStatusTracker(_BaseStatusServiceTestCase):
    @patch.object(InServiceStatusService, "room_assigned")
    def test_tracker_room_assigned_delegates(self, mock_assigned):
        InServiceStatusTracker.room_assigned(self.user, self.project)
        mock_assigned.assert_called_once_with(self.user, self.project)

    @patch.object(InServiceStatusService, "room_closed")
    def test_tracker_room_closed_delegates(self, mock_closed):
        InServiceStatusTracker.room_closed(self.user, self.project)
        mock_closed.assert_called_once_with(self.user, self.project)

    @patch.object(InServiceStatusService, "sync_agent_status")
    def test_tracker_sync_delegates(self, mock_sync):
        InServiceStatusTracker.sync_agent_status(self.user, self.project)
        mock_sync.assert_called_once_with(self.user, self.project)
