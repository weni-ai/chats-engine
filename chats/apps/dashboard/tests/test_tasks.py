from datetime import datetime, timezone as dt_timezone
from unittest.mock import MagicMock, patch, PropertyMock
import io

from django.test import TestCase, override_settings

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import ReportStatus, RoomMetrics
from chats.apps.dashboard.tasks import (
    generate_custom_fields_report,
    process_pending_reports,
    _strip_tz,
    _strip_tz_value,
    _norm_file_type,
)
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class StripTzTests(TestCase):
    def test_strip_tz_value_with_naive_datetime(self):
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        result = _strip_tz_value(naive_dt)
        self.assertEqual(result, naive_dt)

    def test_strip_tz_value_with_aware_datetime(self):
        aware_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        result = _strip_tz_value(aware_dt)
        self.assertIsNone(result.tzinfo)

    def test_strip_tz_value_with_non_datetime(self):
        result = _strip_tz_value("string_value")
        self.assertEqual(result, "string_value")

    def test_strip_tz_with_dict(self):
        data = {"key": datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)}
        result = _strip_tz(data)
        self.assertIsNone(result["key"].tzinfo)

    def test_strip_tz_with_list(self):
        data = [datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)]
        result = _strip_tz(data)
        self.assertIsNone(result[0].tzinfo)


class NormFileTypeTests(TestCase):
    def test_norm_file_type_csv(self):
        self.assertEqual(_norm_file_type("csv"), "csv")
        self.assertEqual(_norm_file_type("CSV"), "csv")
        self.assertEqual(_norm_file_type("text/csv"), "csv")

    def test_norm_file_type_xlsx(self):
        self.assertEqual(_norm_file_type("xlsx"), "xlsx")
        self.assertEqual(_norm_file_type("xls"), "xlsx")
        self.assertEqual(_norm_file_type(None), "xlsx")
        self.assertEqual(_norm_file_type(""), "xlsx")


class GenerateCustomFieldsReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="test@example.com")
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector",
            rooms_limit=5,
            work_start="00:00:00",
            work_end="23:59:59",
            project=self.project,
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create()
        self.room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            is_active=False,
        )
        self.report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_generate_report_success_xlsx(self, mock_viewset_class):
        mock_viewset = MagicMock()
        mock_viewset._generate_report_data.return_value = {
            "rooms": {"data": [{"uuid": str(self.room.uuid), "is_active": False}]}
        }
        mock_viewset_class.return_value = mock_viewset

        fields_config = {
            "rooms": {"fields": ["uuid", "is_active"]},
            "_file_type": "xlsx",
        }

        generate_custom_fields_report(
            self.project.uuid,
            fields_config,
            self.user.email,
            self.report_status.uuid,
        )

        self.report_status.refresh_from_db()
        self.assertEqual(self.report_status.status, "ready")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_generate_report_success_csv(self, mock_viewset_class):
        mock_viewset = MagicMock()
        mock_viewset._generate_report_data.return_value = {
            "rooms": {"data": [{"uuid": str(self.room.uuid), "is_active": False}]}
        }
        mock_viewset_class.return_value = mock_viewset

        fields_config = {
            "rooms": {"fields": ["uuid", "is_active"]},
            "_file_type": "csv",
        }

        generate_custom_fields_report(
            self.project.uuid,
            fields_config,
            self.user.email,
            self.report_status.uuid,
        )

        self.report_status.refresh_from_db()
        self.assertEqual(self.report_status.status, "ready")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_generate_report_failure(self, mock_viewset_class):
        mock_viewset = MagicMock()
        mock_viewset._generate_report_data.side_effect = Exception("Test error")
        mock_viewset_class.return_value = mock_viewset

        fields_config = {"rooms": {"fields": ["uuid"]}}

        with self.assertRaises(Exception):
            generate_custom_fields_report(
                self.project.uuid,
                fields_config,
                self.user.email,
                self.report_status.uuid,
            )

        self.report_status.refresh_from_db()
        self.assertEqual(self.report_status.status, "failed")
        self.assertIn("Test error", self.report_status.error_message)

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_generate_report_with_empty_data(self, mock_viewset_class):
        mock_viewset = MagicMock()
        mock_viewset._generate_report_data.return_value = {"rooms": {"data": []}}
        mock_viewset_class.return_value = mock_viewset

        fields_config = {"rooms": {"fields": ["uuid"]}}

        generate_custom_fields_report(
            self.project.uuid,
            fields_config,
            self.user.email,
            self.report_status.uuid,
        )

        self.report_status.refresh_from_db()
        self.assertEqual(self.report_status.status, "ready")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_generate_report_agent_status_logs(self, mock_viewset_class):
        mock_viewset = MagicMock()
        mock_viewset._generate_report_data.return_value = {
            "agent_status_logs": {"data": [{"uuid": "123", "log_date": "2024-01-01"}]}
        }
        mock_viewset_class.return_value = mock_viewset

        fields_config = {
            "agent_status_logs": {"fields": ["uuid", "log_date"]},
            "_file_type": "xlsx",
        }

        generate_custom_fields_report(
            self.project.uuid,
            fields_config,
            self.user.email,
            self.report_status.uuid,
        )

        self.report_status.refresh_from_db()
        self.assertEqual(self.report_status.status, "ready")

class ProcessPendingReportsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="test@example.com")
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Test Sector",
            rooms_limit=5,
            work_start="00:00:00",
            work_end="23:59:59",
            project=self.project,
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create()
        self.room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            is_active=False,
        )

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    def test_no_pending_reports(self):
        result = process_pending_reports()
        self.assertIsNone(result)

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_xlsx(self, mock_viewset_class):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {"fields": ["uuid"]}, "type": "xlsx"},
        )

        mock_viewset = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 1
        mock_qs.__iter__ = lambda self: iter([{"uuid": "test-uuid"}])
        mock_qs.__getitem__ = lambda self, key: [{"uuid": "test-uuid"}]
        mock_viewset._process_model_fields.return_value = {"queryset": mock_qs}
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "ready")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_csv(self, mock_viewset_class):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {"fields": ["uuid"]}, "type": "csv"},
        )

        mock_viewset = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 1
        mock_qs.__iter__ = lambda self: iter([{"uuid": "test-uuid"}])
        mock_qs.__getitem__ = lambda self, key: [{"uuid": "test-uuid"}]
        mock_viewset._process_model_fields.return_value = {"queryset": mock_qs}
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "ready")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_failure(self, mock_viewset_class):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {"fields": ["uuid"]}},
        )

        mock_viewset = MagicMock()
        mock_viewset._process_model_fields.side_effect = Exception("Processing error")
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "failed")
        self.assertIn("Processing error", report_status.error_message)

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_empty_queryset(self, mock_viewset_class):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {"fields": ["uuid"]}, "type": "xlsx"},
        )

        mock_viewset = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 0
        mock_viewset._process_model_fields.return_value = {"queryset": mock_qs}
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "ready")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_agent_status_logs(self, mock_viewset_class):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={
                "agent_status_logs": {"fields": ["uuid", "log_date"]},
                "type": "xlsx",
            },
        )

        mock_viewset = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 1
        mock_qs.__iter__ = lambda self: iter([{"uuid": "123", "log_date": "2024-01-01"}])
        mock_qs.__getitem__ = lambda self, key: [{"uuid": "123", "log_date": "2024-01-01"}]
        mock_viewset._process_model_fields.return_value = {"queryset": mock_qs}
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "ready")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    def test_process_oldest_pending_report_first(self):
        older_report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )
        newer_report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        with patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet") as mock_viewset_class:
            mock_viewset = MagicMock()
            mock_viewset._process_model_fields.return_value = {"queryset": None}
            mock_viewset_class.return_value = mock_viewset

            process_pending_reports()

        older_report.refresh_from_db()
        newer_report.refresh_from_db()

        self.assertEqual(older_report.status, "ready")
        self.assertEqual(newer_report.status, "pending")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False, REPORTS_CHUNK_SIZE=100)
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_large_dataset(self, mock_viewset_class):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {"fields": ["uuid"]}, "type": "xlsx"},
        )

        mock_viewset = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 5000
        mock_qs.__iter__ = lambda self: iter([{"uuid": f"uuid-{i}"} for i in range(100)])
        mock_qs.__getitem__ = lambda self, key: [{"uuid": f"uuid-{i}"} for i in range(100)]
        mock_viewset._process_model_fields.return_value = {"queryset": mock_qs}
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "ready")

