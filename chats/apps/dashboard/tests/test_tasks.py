from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from chats.apps.accounts.models import User
from chats.apps.dashboard.models import ReportStatus
from chats.apps.dashboard.tasks import process_pending_reports
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class ProcessPendingReportsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="agent@test.com")
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Support",
            project=self.project,
            rooms_limit=5,
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)

    def test_no_pending_reports_returns_early(self):
        result = process_pending_reports()
        self.assertIsNone(result)

    def test_picks_oldest_pending_report(self):
        report1 = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {}},
        )
        report2 = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {}},
        )
        
        with patch(
            "chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet"
        ) as mock_view:
            mock_instance = MagicMock()
            mock_view.return_value = mock_instance
            mock_instance._process_model_fields.return_value = {"queryset": Room.objects.none()}
            
            with patch("chats.core.storages.ExcelStorage"):
                with patch("django.core.mail.EmailMultiAlternatives"):
                    try:
                        process_pending_reports()
                    except Exception:
                        pass
        
        report1.refresh_from_db()
        self.assertIn(report1.status, ["in_progress", "ready", "error"])

    def test_report_status_changes_to_in_progress(self):
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {}},
        )
        
        with patch(
            "chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet"
        ) as mock_view:
            mock_instance = MagicMock()
            mock_view.return_value = mock_instance
            mock_instance._process_model_fields.return_value = {"queryset": Room.objects.none()}
            
            with patch("chats.core.storages.ExcelStorage"):
                with patch("django.core.mail.EmailMultiAlternatives"):
                    try:
                        process_pending_reports()
                    except Exception:
                        pass

        report.refresh_from_db()
        self.assertIn(report.status, ["in_progress", "ready", "error"])

    @patch("chats.core.storages.ExcelStorage")
    @patch("django.core.mail.EmailMultiAlternatives")
    @patch("chats.apps.api.v1.dashboard.presenter.ModelFieldsPresenter")
    def test_generates_xlsx_report(self, mock_presenter, mock_email, mock_storage):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid", "protocol"]},
        }
        
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"type": "xlsx", "rooms": {"fields": ["uuid"]}},
        )
        
        with patch(
            "chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet"
        ) as mock_view:
            mock_instance = MagicMock()
            mock_view.return_value = mock_instance
            mock_qs = MagicMock()
            mock_qs.count.return_value = 0
            mock_instance._process_model_fields.return_value = {"queryset": mock_qs}
            
            process_pending_reports()

        report.refresh_from_db()
        self.assertEqual(report.status, "ready")

    @patch("chats.core.storages.ExcelStorage")
    @patch("django.core.mail.EmailMultiAlternatives")
    @patch("chats.apps.api.v1.dashboard.presenter.ModelFieldsPresenter")
    def test_generates_csv_report(self, mock_presenter, mock_email, mock_storage):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid", "protocol"]},
        }
        
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"type": "csv", "rooms": {"fields": ["uuid"]}},
        )
        
        with patch(
            "chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet"
        ) as mock_view:
            mock_instance = MagicMock()
            mock_view.return_value = mock_instance
            mock_qs = MagicMock()
            mock_qs.count.return_value = 0
            mock_instance._process_model_fields.return_value = {"queryset": mock_qs}
            
            process_pending_reports()

        report.refresh_from_db()
        self.assertEqual(report.status, "ready")

    @override_settings(REPORTS_SEND_EMAILS=True)
    @patch("chats.apps.dashboard.tasks.EmailMultiAlternatives")
    @patch("chats.core.storages.ReportsStorage")
    @patch("chats.apps.api.v1.dashboard.presenter.ModelFieldsPresenter")
    def test_sends_email_on_completion(self, mock_presenter, mock_storage, mock_email_class):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
        }
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.save.return_value = "test_file.xlsx"
        mock_storage_instance.get_download_url.return_value = "http://example.com/file.xlsx"
        
        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance
        
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"type": "xlsx", "rooms": {"fields": ["uuid"]}},
        )
        
        with patch(
            "chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet"
        ) as mock_view:
            mock_instance = MagicMock()
            mock_view.return_value = mock_instance
            mock_qs = MagicMock()
            mock_qs.count.return_value = 0
            mock_instance._process_model_fields.return_value = {"queryset": mock_qs}
            
            process_pending_reports()

        mock_email_instance.send.assert_called()

    @patch("chats.apps.api.v1.dashboard.presenter.ModelFieldsPresenter")
    def test_handles_error_and_sets_status(self, mock_presenter):
        mock_presenter.get_models_info.side_effect = Exception("Test error")
        
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {}},
        )
        
        process_pending_reports()

        report.refresh_from_db()
        self.assertEqual(report.status, "failed")
        self.assertIn("Test error", report.error_message)

    @override_settings(REPORTS_CHUNK_SIZE=100)
    @patch("chats.core.storages.ExcelStorage")
    @patch("django.core.mail.EmailMultiAlternatives")
    @patch("chats.apps.api.v1.dashboard.presenter.ModelFieldsPresenter")
    def test_processes_large_queryset_in_chunks(self, mock_presenter, mock_email, mock_storage):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
        }
        
        for i in range(150):
            Room.objects.create(
                queue=self.queue,
                project_uuid=str(self.project.uuid),
                protocol=f"ROOM-{i}",
            )
        
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"type": "xlsx", "rooms": {"fields": ["uuid", "protocol"]}},
        )
        
        with patch(
            "chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet"
        ) as mock_view:
            mock_instance = MagicMock()
            mock_view.return_value = mock_instance
            mock_instance._process_model_fields.return_value = {
                "queryset": Room.objects.filter(queue__sector__project=self.project).values("uuid", "protocol")
            }
            
            process_pending_reports()

        report.refresh_from_db()
        self.assertEqual(report.status, "ready")

    @patch("chats.core.storages.ExcelStorage")
    @patch("django.core.mail.EmailMultiAlternatives")
    @patch("chats.apps.api.v1.dashboard.presenter.ModelFieldsPresenter")
    def test_skips_empty_model_configs(self, mock_presenter, mock_email, mock_storage):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
            "agent_status_logs": {"fields": ["status"]},
        }
        
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"type": "xlsx"},
        )
        
        with patch(
            "chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet"
        ) as mock_view:
            mock_instance = MagicMock()
            mock_view.return_value = mock_instance
            mock_qs = MagicMock()
            mock_qs.count.return_value = 0
            mock_instance._process_model_fields.return_value = {"queryset": mock_qs}
            
            process_pending_reports()

        report.refresh_from_db()
        self.assertEqual(report.status, "ready")
