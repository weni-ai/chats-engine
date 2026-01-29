from datetime import timedelta
import uuid
from django.test import TestCase, override_settings
from unittest.mock import MagicMock, call, patch
from dateutil.relativedelta import relativedelta as rdelta

from django.utils import timezone
from chats.apps.archive_chats.choices import ArchiveConversationsJobStatus
from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.apps.archive_chats.services import ArchiveChatsService
from chats.apps.archive_chats.tasks import (
    archive_room_messages,
    start_archive_rooms_messages,
)
from chats.apps.rooms.models import Room
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue

service = MagicMock(spec=ArchiveChatsService)


class TestStartArchiveRoomsMessages(TestCase):
    def setUp(self):
        service.reset_mock()

    @override_settings(ARCHIVE_CHATS_MAX_ROOMS=50)
    @override_settings(ARCHIVE_CHATS_IS_ACTIVE_FOR_ALL_PROJECTS=True)
    @patch("chats.apps.archive_chats.tasks.ArchiveChatsService", return_value=service)
    @patch("chats.apps.archive_chats.tasks.archive_room_messages.apply_async")
    @patch("chats.apps.archive_chats.tasks.calculate_archive_task_expiration_dt")
    def test_start_archive_rooms_messages(
        self,
        mock_calculate_archive_task_expiration_dt,
        mock_archive_room_messages_apply_async,
        mock_archive_chats_service,
    ):
        mock_archive_room_messages_apply_async.return_value = None

        expiration_dt = timezone.now() + timedelta(hours=1)
        mock_calculate_archive_task_expiration_dt.return_value = expiration_dt

        job = ArchiveConversationsJob.objects.create(
            started_at=timezone.now(),
        )
        service.start_archive_job.return_value = job

        # Should be included
        rooms = [
            Room.objects.create(
                is_active=False,
                ended_at=timezone.now() - rdelta(years=1),
            )
            for _ in range(2)
        ]

        # Should not be included because is active
        Room.objects.create(is_active=True)
        # Should not be included because ended_at is not more than 1 year ago
        Room.objects.create(is_active=False, ended_at=timezone.now() - rdelta(days=3))
        # Should not be included because room was already archived
        room = Room.objects.create(
            is_active=False, ended_at=timezone.now() - rdelta(years=1)
        )
        RoomArchivedConversation.objects.create(
            room=room, job=job, status=ArchiveConversationsJobStatus.FINISHED
        )

        start_archive_rooms_messages()

        service.start_archive_job.assert_called_once()

        expected_calls = [
            call(
                args=[room.uuid, job.uuid],
                expires=expiration_dt,
            )
            for room in rooms
        ]

        mock_archive_room_messages_apply_async.assert_has_calls(
            expected_calls,
            any_order=True,
        )

        assert mock_archive_room_messages_apply_async.call_count == len(rooms)

    @override_settings(ARCHIVE_CHATS_MAX_ROOMS=50)
    @override_settings(ARCHIVE_CHATS_IS_ACTIVE_FOR_ALL_PROJECTS=False)
    @patch("chats.apps.archive_chats.tasks.ArchiveChatsService", return_value=service)
    @patch("chats.apps.archive_chats.tasks.archive_room_messages.apply_async")
    @patch("chats.apps.archive_chats.tasks.calculate_archive_task_expiration_dt")
    def test_start_archive_rooms_messages_when_not_active_for_all_projects_and_projects_list_is_empty(
        self,
        mock_calculate_archive_task_expiration_dt,
        mock_archive_room_messages_apply_async,
        mock_archive_chats_service,
    ):
        mock_archive_room_messages_apply_async.return_value = None

        expiration_dt = timezone.now() + timedelta(hours=1)
        mock_calculate_archive_task_expiration_dt.return_value = expiration_dt

        job = ArchiveConversationsJob.objects.create(
            started_at=timezone.now(),
        )
        service.start_archive_job.return_value = job

        # Should be included
        for _ in range(2):
            Room.objects.create(
                is_active=False,
                ended_at=timezone.now() - rdelta(years=1),
            )

        # Should not be included because is active
        Room.objects.create(is_active=True)
        # Should not be included because ended_at is not more than 1 year ago
        Room.objects.create(is_active=False, ended_at=timezone.now() - rdelta(days=3))
        # Should not be included because room was already archived
        room = Room.objects.create(
            is_active=False, ended_at=timezone.now() - rdelta(years=1)
        )
        RoomArchivedConversation.objects.create(
            room=room, job=job, status=ArchiveConversationsJobStatus.FINISHED
        )

        start_archive_rooms_messages()

        service.start_archive_job.assert_called_once()
        mock_archive_room_messages_apply_async.assert_not_called()

    @override_settings(ARCHIVE_CHATS_MAX_ROOMS=50)
    @override_settings(ARCHIVE_CHATS_IS_ACTIVE_FOR_ALL_PROJECTS=False)
    @patch("chats.apps.archive_chats.tasks.ArchiveChatsService", return_value=service)
    @patch("chats.apps.archive_chats.tasks.archive_room_messages.apply_async")
    @patch("chats.apps.archive_chats.tasks.calculate_archive_task_expiration_dt")
    def test_start_archive_rooms_messages_when_not_active_for_all_projects_and_projects_list_is_not_empty(
        self,
        mock_calculate_archive_task_expiration_dt,
        mock_archive_room_messages_apply_async,
        mock_archive_chats_service,
    ):
        mock_archive_room_messages_apply_async.return_value = None

        expiration_dt = timezone.now() + timedelta(hours=1)
        mock_calculate_archive_task_expiration_dt.return_value = expiration_dt

        project = Project.objects.create(name="Test Project")
        sector = Sector.objects.create(
            name="Test Sector",
            project=project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        queue = Queue.objects.create(name="Test Queue", sector=sector)

        job = ArchiveConversationsJob.objects.create(
            started_at=timezone.now(),
        )
        service.start_archive_job.return_value = job
        service.get_projects.return_value = [project.uuid]

        # Should be included
        rooms = [
            Room.objects.create(
                is_active=False,
                ended_at=timezone.now() - rdelta(years=1),
                queue=queue,
            )
            for _ in range(2)
        ]

        # Should not be included because is active
        Room.objects.create(is_active=True)
        # Should not be included because ended_at is not more than 1 year ago
        Room.objects.create(is_active=False, ended_at=timezone.now() - rdelta(days=3))
        # Should not be included because room was already archived
        room = Room.objects.create(
            is_active=False, ended_at=timezone.now() - rdelta(years=1)
        )
        RoomArchivedConversation.objects.create(
            room=room, job=job, status=ArchiveConversationsJobStatus.FINISHED
        )

        start_archive_rooms_messages()

        service.start_archive_job.assert_called_once()

        expected_calls = [
            call(
                args=[room.uuid, job.uuid],
                expires=expiration_dt,
            )
            for room in rooms
        ]

        mock_archive_room_messages_apply_async.assert_has_calls(
            expected_calls,
            any_order=True,
        )

        assert mock_archive_room_messages_apply_async.call_count == len(rooms)

    @override_settings(ARCHIVE_CHATS_MAX_ROOMS=2)
    @override_settings(ARCHIVE_CHATS_IS_ACTIVE_FOR_ALL_PROJECTS=True)
    @patch("chats.apps.archive_chats.tasks.ArchiveChatsService", return_value=service)
    @patch("chats.apps.archive_chats.tasks.archive_room_messages.apply_async")
    @patch("chats.apps.archive_chats.tasks.calculate_archive_task_expiration_dt")
    def test_start_archive_rooms_messages_with_max_rooms_reached(
        self,
        mock_calculate_archive_task_expiration_dt,
        mock_archive_room_messages_apply_async,
        mock_archive_chats_service,
    ):
        mock_archive_room_messages_apply_async.return_value = None

        expiration_dt = timezone.now() + timedelta(hours=1)
        mock_calculate_archive_task_expiration_dt.return_value = expiration_dt

        job = ArchiveConversationsJob.objects.create(
            started_at=timezone.now(),
        )
        service.start_archive_job.return_value = job

        # Should be included
        rooms = [
            Room.objects.create(
                is_active=False,
                ended_at=timezone.now() - rdelta(years=1),
            )
            for _ in range(2)
        ]

        # Should not be included because the maximum number of rooms has been reached (2)
        Room.objects.create(is_active=False, ended_at=timezone.now() - rdelta(years=1))

        start_archive_rooms_messages()

        service.start_archive_job.assert_called_once()

        expected_calls = [
            call(
                args=[room.uuid, job.uuid],
                expires=expiration_dt,
            )
            for room in rooms
        ]

        mock_archive_room_messages_apply_async.assert_has_calls(
            expected_calls,
            any_order=True,
        )

        assert mock_archive_room_messages_apply_async.call_count == len(rooms)


class TestArchiveRoomMessages(TestCase):
    def setUp(self):
        service.reset_mock()

    @patch("chats.apps.archive_chats.tasks.ArchiveChatsService", return_value=service)
    def test_archive_room_messages(self, mock_archive_chats_service):
        room = Room.objects.create(
            is_active=False, ended_at=timezone.now() - rdelta(years=1)
        )
        job = ArchiveConversationsJob.objects.create(started_at=timezone.now())
        service.archive_room_history.return_value = None

        archive_room_messages(room.uuid, job.uuid)

        service.archive_room_history.assert_called_once_with(room, job)

    def test_archive_room_messages_with_job_not_found(self):
        archive_room_messages(uuid.uuid4(), uuid.uuid4())

        service.archive_room_history.assert_not_called()

    def test_archive_room_messages_with_room_not_found(self):
        job = ArchiveConversationsJob.objects.create(started_at=timezone.now())
        archive_room_messages(uuid.uuid4(), job.uuid)

        service.archive_room_history.assert_not_called()
