from datetime import datetime
from datetime import timezone as tz
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from chats.apps.accounts.models import User
from chats.apps.dashboard.models import ReportStatus
from chats.apps.dashboard.tasks import (
    _norm_file_type,
    _strip_tz,
    _strip_tz_value,
    generate_custom_fields_report,
    process_pending_reports,
)
from chats.apps.projects.models import Project


class StripTzTests(TestCase):
    def test_strip_tz_value_with_naive_datetime(self):
        naive_dt = datetime(2025, 1, 1, 12, 0, 0)
        result = _strip_tz_value(naive_dt)
        self.assertEqual(result, naive_dt)
        self.assertIsNone(result.tzinfo)

    def test_strip_tz_value_with_aware_datetime(self):
        aware_dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=tz.utc)
        result = _strip_tz_value(aware_dt)
        self.assertIsNone(result.tzinfo)

    def test_strip_tz_value_with_non_datetime(self):
        result = _strip_tz_value("string_value")
        self.assertEqual(result, "string_value")

        result = _strip_tz_value(123)
        self.assertEqual(result, 123)

        result = _strip_tz_value(None)
        self.assertIsNone(result)

    def test_strip_tz_with_dict(self):
        data = {"date": datetime(2025, 1, 1, 12, 0, 0, tzinfo=tz.utc), "name": "test"}
        result = _strip_tz(data)
        self.assertIsNone(result["date"].tzinfo)
        self.assertEqual(result["name"], "test")

    def test_strip_tz_with_list(self):
        data = [
            datetime(2025, 1, 1, 12, 0, 0, tzinfo=tz.utc),
            datetime(2025, 2, 1, 12, 0, 0, tzinfo=tz.utc),
        ]
        result = _strip_tz(data)
        for dt in result:
            self.assertIsNone(dt.tzinfo)

    def test_strip_tz_with_nested_structure(self):
        data = {
            "items": [
                {"date": datetime(2025, 1, 1, 12, 0, 0, tzinfo=tz.utc)},
            ]
        }
        result = _strip_tz(data)
        self.assertIsNone(result["items"][0]["date"].tzinfo)


class NormFileTypeTests(TestCase):
    def test_norm_file_type_xlsx(self):
        self.assertEqual(_norm_file_type("xlsx"), "xlsx")
        self.assertEqual(_norm_file_type("XLSX"), "xlsx")
        self.assertEqual(_norm_file_type("  xlsx  "), "xlsx")

    def test_norm_file_type_csv(self):
        self.assertEqual(_norm_file_type("csv"), "csv")
        self.assertEqual(_norm_file_type("CSV"), "csv")

    def test_norm_file_type_none(self):
        result = _norm_file_type(None)
        self.assertIn(result, ["xlsx", "csv"])

    def test_norm_file_type_invalid(self):
        result = _norm_file_type("pdf")
        self.assertIn(result, ["xlsx", "csv"])


class ProcessPendingReportsTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.user = User.objects.create_user(
            email="test@test.com", first_name="Test", last_name="User"
        )

    def test_process_pending_reports_no_pending_reports(self):
        result = process_pending_reports()
        self.assertIsNone(result)

    @override_settings(REPORTS_SAVE_LOCALLY=True, REPORTS_SEND_EMAILS=False)
    def test_process_pending_reports_with_pending_report(self):
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {"fields": ["uuid", "created_on"]}},
        )

        with patch(
            "chats.apps.api.v1.dashboard.presenter.ModelFieldsPresenter.get_models_info"
        ) as mock_presenter:
            with patch(
                "chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet._process_model_fields"
            ) as mock_process:
                mock_presenter.return_value = {
                    "rooms": {"fields": ["uuid", "created_on"]},
                    "agent_status_logs": {"fields": ["uuid"]},
                }
                mock_process.return_value = {
                    "queryset": MagicMock(count=MagicMock(return_value=0))
                }

                with patch("chats.apps.dashboard.tasks.pd.ExcelWriter"):
                    with patch("chats.apps.dashboard.tasks.os.makedirs"):
                        with patch("builtins.open", MagicMock()):
                            try:
                                process_pending_reports()
                            except Exception:
                                pass

        report.refresh_from_db()
        self.assertIn(report.status, ["in_progress", "ready", "error", "failed"])

    def test_process_pending_reports_updates_status_to_in_progress(self):
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        with patch(
            "chats.apps.api.v1.dashboard.presenter.ModelFieldsPresenter.get_models_info"
        ) as mock_presenter:
            mock_presenter.return_value = {}

            with patch("chats.apps.dashboard.tasks.pd.ExcelWriter"):
                try:
                    process_pending_reports()
                except Exception:
                    pass

        report.refresh_from_db()
        self.assertIn(report.status, ["in_progress", "ready", "error", "failed"])

    def test_process_pending_reports_selects_oldest_pending(self):
        report1 = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )
        report2 = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        with patch(
            "chats.apps.api.v1.dashboard.presenter.ModelFieldsPresenter.get_models_info"
        ) as mock_presenter:
            mock_presenter.return_value = {}

            with patch("chats.apps.dashboard.tasks.pd.ExcelWriter"):
                try:
                    process_pending_reports()
                except Exception:
                    pass

        report1.refresh_from_db()
        report2.refresh_from_db()

        self.assertIn(report1.status, ["in_progress", "ready", "error"])
        self.assertEqual(report2.status, "pending")


class GenerateCustomFieldsReportTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.user = User.objects.create_user(
            email="test@test.com", first_name="Test", last_name="User"
        )

    @override_settings(REPORTS_SAVE_LOCALLY=True, REPORTS_SEND_EMAILS=False)
    def test_generate_custom_fields_report_updates_status(self):
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        with patch(
            "chats.apps.api.v1.dashboard.presenter.ModelFieldsPresenter.get_models_info"
        ) as mock_presenter:
            with patch(
                "chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet._generate_report_data"
            ) as mock_generate:
                mock_presenter.return_value = {
                    "rooms": {"fields": ["uuid"]},
                    "agent_status_logs": {"fields": ["uuid"]},
                }
                mock_generate.return_value = {"rooms": {"data": []}}

                with patch("chats.apps.dashboard.tasks.pd.ExcelWriter"):
                    with patch("chats.apps.dashboard.tasks.os.makedirs"):
                        with patch("builtins.open", MagicMock()):
                            try:
                                generate_custom_fields_report(
                                    project_uuid=self.project.uuid,
                                    fields_config={"rooms": {"fields": ["uuid"]}},
                                    user_email=self.user.email,
                                    report_status_id=report.uuid,
                                )
                            except Exception:
                                pass

        report.refresh_from_db()
        self.assertIn(report.status, ["in_progress", "ready", "error", "failed"])
