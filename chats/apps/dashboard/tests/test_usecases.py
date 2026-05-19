from django.core.cache import cache
from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.dashboard.models import ReportStatus
from chats.apps.dashboard.usecases import (
    REPORT_STATUS_CACHE_KEY_TEMPLATE,
    GetReportStatusUseCase,
    InvalidateReportStatusCacheUseCase,
)
from chats.apps.projects.models import Project


class GetReportStatusUseCaseTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create(email="report-user@test.com")
        self.project = Project.objects.create(name="Test Project")
        self.use_case = GetReportStatusUseCase()

    def test_returns_ready_when_no_active_reports(self):
        result = self.use_case.execute(self.project)

        self.assertEqual(result["status"], "ready")
        self.assertIsNone(result["email"])
        self.assertIsNone(result["report_uuid"])

    def test_returns_pending_report_data(self):
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        result = self.use_case.execute(self.project)

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["email"], self.user.email)
        self.assertEqual(result["report_uuid"], str(report.uuid))

    def test_returns_in_progress_report_data(self):
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="in_progress",
            fields_config={},
        )

        result = self.use_case.execute(self.project)

        self.assertEqual(result["status"], "in_progress")
        self.assertEqual(result["email"], self.user.email)
        self.assertEqual(result["report_uuid"], str(report.uuid))

    def test_ignores_completed_reports(self):
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="ready",
            fields_config={},
        )

        result = self.use_case.execute(self.project)

        self.assertEqual(result["status"], "ready")
        self.assertIsNone(result["email"])
        self.assertIsNone(result["report_uuid"])

    def test_returns_latest_active_report(self):
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )
        latest_report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="in_progress",
            fields_config={},
        )

        result = self.use_case.execute(self.project)

        self.assertEqual(result["report_uuid"], str(latest_report.uuid))

    def test_caches_result_on_first_call(self):
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        self.use_case.execute(self.project)

        cache_key = REPORT_STATUS_CACHE_KEY_TEMPLATE.format(
            project_uuid=self.project.uuid,
        )
        self.assertIsNotNone(cache.get(cache_key))

    def test_returns_cached_data_without_extra_queries(self):
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        self.use_case.execute(self.project)

        with self.assertNumQueries(0):
            self.use_case.execute(self.project)

    def test_returns_fresh_data_after_cache_invalidation(self):
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        self.use_case.execute(self.project)

        report.status = "ready"
        report.save()

        InvalidateReportStatusCacheUseCase().execute(
            project_uuid=str(self.project.uuid),
        )

        result = self.use_case.execute(self.project)

        self.assertEqual(result["status"], "ready")
        self.assertIsNone(result["email"])
        self.assertIsNone(result["report_uuid"])


class InvalidateReportStatusCacheUseCaseTests(TestCase):
    def setUp(self):
        cache.clear()
        self.project = Project.objects.create(name="Test Project")
        self.use_case = InvalidateReportStatusCacheUseCase()

    def test_deletes_cache_key(self):
        cache_key = REPORT_STATUS_CACHE_KEY_TEMPLATE.format(
            project_uuid=self.project.uuid,
        )
        cache.set(cache_key, {"status": "pending"})

        self.use_case.execute(project_uuid=str(self.project.uuid))

        self.assertIsNone(cache.get(cache_key))

    def test_no_error_when_key_does_not_exist(self):
        self.use_case.execute(project_uuid=str(self.project.uuid))
