from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.dashboard.models import ReportStatus
from chats.apps.projects.models import Project


class ReportStatusSignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="signal-user@test.com")
        self.project = Project.objects.create(name="Signal Project")

    @patch(
        "chats.apps.dashboard.signals.InvalidateReportStatusCacheUseCase.execute"
    )
    def test_creating_report_status_invalidates_cache(self, mock_execute):
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        mock_execute.assert_called_once_with(
            project_uuid=str(self.project.pk),
        )

    @patch(
        "chats.apps.dashboard.signals.InvalidateReportStatusCacheUseCase.execute"
    )
    def test_updating_report_status_invalidates_cache(self, mock_execute):
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        mock_execute.reset_mock()

        report.status = "in_progress"
        report.save()

        mock_execute.assert_called_once_with(
            project_uuid=str(self.project.pk),
        )

    @patch(
        "chats.apps.dashboard.signals.InvalidateReportStatusCacheUseCase.execute"
    )
    def test_signal_passes_correct_project_uuid(self, mock_execute):
        other_project = Project.objects.create(name="Other Project")

        ReportStatus.objects.create(
            project=other_project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        mock_execute.assert_called_once_with(
            project_uuid=str(other_project.pk),
        )
