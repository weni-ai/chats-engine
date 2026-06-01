from datetime import time
from unittest.mock import patch

from django.test import TestCase, override_settings

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import ReportStatus
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.rooms.tasks import (
    _select_room_export_to_process,
    generate_room_export,
    process_pending_room_exports,
)
from chats.apps.sectors.models import Sector


class RoomExportTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="agent@example.com")
        self.project = Project.objects.create(name="Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(hour=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(external_id="contact-1", name="Contact")
        self.room = Room.objects.create(
            contact=self.contact, queue=self.queue, user=self.user
        )
        Room.objects.filter(pk=self.room.pk).update(
            is_active=False, ended_at=self.room.created_on
        )
        self.room.refresh_from_db()

        self.report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            room=self.room,
            report_type=ReportStatus.REPORT_TYPE_ROOM_EXPORT,
            fields_config={"types": ["html", "pdf"]},
            status="pending",
        )

    @override_settings(REPORTS_SEND_EMAILS=True)
    @patch("chats.apps.rooms.tasks.SendRoomExportEmail")
    @patch("chats.apps.rooms.tasks.RenderRoomExport")
    @patch("chats.apps.rooms.tasks.BuildRoomExportData")
    def test_generate_marks_report_as_ready_on_success(
        self, mock_build, mock_render, mock_send
    ):
        mock_build.return_value.execute.return_value = {"room": {}}
        mock_render.return_value.execute.return_value = {
            "html": b"<html/>",
            "pdf": b"%PDF",
        }

        generate_room_export(str(self.report.uuid))

        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "ready")
        mock_build.return_value.execute.assert_called_once_with(
            self.room, generated_by=self.user.email
        )
        mock_render.return_value.execute.assert_called_once()
        mock_send.return_value.execute.assert_called_once()

    @override_settings(REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.rooms.tasks.SendRoomExportEmail")
    @patch("chats.apps.rooms.tasks.RenderRoomExport")
    @patch("chats.apps.rooms.tasks.BuildRoomExportData")
    def test_generate_skips_email_when_flag_disabled(
        self, mock_build, mock_render, mock_send
    ):
        mock_build.return_value.execute.return_value = {}
        mock_render.return_value.execute.return_value = {"html": b"<html/>"}

        generate_room_export(str(self.report.uuid))

        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "ready")
        mock_send.return_value.execute.assert_not_called()

    @override_settings(REPORTS_SEND_EMAILS=True)
    @patch("chats.apps.rooms.tasks.SendRoomExportEmail")
    @patch("chats.apps.rooms.tasks.RenderRoomExport")
    @patch("chats.apps.rooms.tasks.BuildRoomExportData")
    def test_generate_increments_retry_on_failure(
        self, mock_build, mock_render, mock_send
    ):
        mock_build.return_value.execute.side_effect = RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            generate_room_export(str(self.report.uuid))

        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "failed")
        self.assertEqual(self.report.retry_count, 1)
        self.assertIn("boom", self.report.error_message)
        mock_send.return_value.send_failure_notification.assert_not_called()

    @override_settings(REPORTS_SEND_EMAILS=True)
    @patch("chats.apps.rooms.tasks.SendRoomExportEmail")
    @patch("chats.apps.rooms.tasks.RenderRoomExport")
    @patch("chats.apps.rooms.tasks.BuildRoomExportData")
    def test_generate_marks_permanently_failed_after_max_retries(
        self, mock_build, mock_render, mock_send
    ):
        self.report.retry_count = ReportStatus.MAX_RETRY_COUNT - 1
        self.report.save()
        mock_build.return_value.execute.side_effect = RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            generate_room_export(str(self.report.uuid))

        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "permanently_failed")
        mock_send.return_value.send_failure_notification.assert_called_once()

    def test_generate_rejects_non_room_export_report(self):
        other_report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            report_type=ReportStatus.REPORT_TYPE_CUSTOM_DASHBOARD,
            fields_config={},
        )
        with self.assertRaises(ValueError):
            generate_room_export(str(other_report.uuid))

    @override_settings(REPORTS_SEND_EMAILS=True)
    @patch("chats.apps.rooms.tasks.SendRoomExportEmail")
    @patch("chats.apps.rooms.tasks.RenderRoomExport")
    @patch("chats.apps.rooms.tasks.BuildRoomExportData")
    def test_process_pending_picks_only_room_exports(
        self, mock_build, mock_render, mock_send
    ):
        dashboard_report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            report_type=ReportStatus.REPORT_TYPE_CUSTOM_DASHBOARD,
            fields_config={},
            status="pending",
        )
        mock_build.return_value.execute.return_value = {}
        mock_render.return_value.execute.return_value = {"html": b"<html/>"}

        process_pending_room_exports()

        self.report.refresh_from_db()
        dashboard_report.refresh_from_db()
        self.assertEqual(self.report.status, "ready")
        self.assertEqual(dashboard_report.status, "pending")

    def test_select_returns_none_when_no_pending_room_exports(self):
        self.report.status = "ready"
        self.report.save()
        result = _select_room_export_to_process()
        self.assertIsNone(result)
