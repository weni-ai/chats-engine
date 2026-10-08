from datetime import datetime
from datetime import timezone as dt_timezone
from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase, override_settings

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import ReportStatus
from chats.apps.api.v1.dashboard.presenter import ModelFieldsPresenter
from chats.apps.api.v1.dashboard.viewsets import ReportFieldsValidatorViewSet
from chats.apps.dashboard.tasks import (
    _norm_file_type,
    _strip_tz,
    _strip_tz_value,
    generate_custom_fields_report,
    process_pending_reports,
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
            "rooms": {"data": [{"protocol": str(self.room.uuid), "is_active": False}]}
        }
        mock_viewset_class.return_value = mock_viewset

        fields_config = {
            "rooms": {"fields": ["protocol", "is_active"]},
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
            "rooms": {"data": [{"protocol": str(self.room.uuid), "is_active": False}]}
        }
        mock_viewset_class.return_value = mock_viewset

        fields_config = {
            "rooms": {"fields": ["protocol", "is_active"]},
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

        fields_config = {"rooms": {"fields": ["is_active"]}}

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

        fields_config = {"rooms": {"fields": ["is_active"]}}

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
            "agent_status_logs": {"data": [{"agent__email": "a@test.com", "log_date": "2024-01-01"}]}
        }
        mock_viewset_class.return_value = mock_viewset

        fields_config = {
            "agent_status_logs": {"fields": ["agent__email", "log_date"]},
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
    @patch("chats.apps.dashboard.tasks.ExcelStorage")
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_xlsx(self, mock_viewset_class, mock_storage_class):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {"fields": ["is_active"]}, "type": "xlsx"},
        )

        mock_storage = MagicMock()
        mock_storage.listdir.return_value = ([], [])
        mock_storage_class.return_value = mock_storage

        mock_viewset = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 1
        mock_qs.__iter__ = lambda self: iter([{"is_active": False}])
        mock_qs.__getitem__ = lambda self, key: [{"is_active": False}]
        mock_viewset._process_model_fields.return_value = {"queryset": mock_qs}
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "ready")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.dashboard.tasks.ExcelStorage")
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_csv(self, mock_viewset_class, mock_storage_class):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {"fields": ["is_active"]}, "type": "csv"},
        )

        mock_storage = MagicMock()
        mock_storage.listdir.return_value = ([], [])
        mock_storage_class.return_value = mock_storage

        mock_viewset = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 1
        mock_qs.__iter__ = lambda self: iter([{"is_active": False}])
        mock_qs.__getitem__ = lambda self, key: [{"is_active": False}]
        mock_viewset._process_model_fields.return_value = {"queryset": mock_qs}
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "ready")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.dashboard.tasks.ExcelStorage")
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_failure(
        self, mock_viewset_class, mock_storage_class
    ):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {"fields": ["is_active"]}},
        )

        mock_storage = MagicMock()
        mock_storage.listdir.return_value = ([], [])
        mock_storage_class.return_value = mock_storage

        mock_viewset = MagicMock()
        mock_viewset._process_model_fields.side_effect = Exception("Processing error")
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "failed")
        self.assertIn("Processing error", report_status.error_message)

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.dashboard.tasks.ExcelStorage")
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_empty_queryset(
        self, mock_viewset_class, mock_storage_class
    ):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {"fields": ["is_active"]}, "type": "xlsx"},
        )

        mock_storage = MagicMock()
        mock_storage.listdir.return_value = ([], [])
        mock_storage_class.return_value = mock_storage

        mock_viewset = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 0
        mock_viewset._process_model_fields.return_value = {"queryset": mock_qs}
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "ready")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.dashboard.tasks.ExcelStorage")
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_agent_status_logs(
        self, mock_viewset_class, mock_storage_class
    ):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={
                "agent_status_logs": {"fields": ["agent__email", "log_date"]},
                "type": "xlsx",
            },
        )

        mock_storage = MagicMock()
        mock_storage.listdir.return_value = ([], [])
        mock_storage_class.return_value = mock_storage

        mock_viewset = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 1
        mock_qs.__iter__ = lambda self: iter(
            [{"agent__email": "a@test.com", "log_date": "2024-01-01"}]
        )
        mock_qs.__getitem__ = lambda self, key: [
            {"agent__email": "a@test.com", "log_date": "2024-01-01"}
        ]
        mock_viewset._process_model_fields.return_value = {"queryset": mock_qs}
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "ready")

    @override_settings(REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False)
    @patch("chats.apps.dashboard.tasks.ExcelStorage")
    def test_process_oldest_pending_report_first(self, mock_storage_class):
        mock_storage = MagicMock()
        mock_storage.listdir.return_value = ([], [])
        mock_storage_class.return_value = mock_storage

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

        with patch(
            "chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet"
        ) as mock_viewset_class:
            mock_viewset = MagicMock()
            mock_viewset._process_model_fields.return_value = {"queryset": None}
            mock_viewset_class.return_value = mock_viewset

            process_pending_reports()

        older_report.refresh_from_db()
        newer_report.refresh_from_db()

        self.assertEqual(older_report.status, "ready")
        self.assertEqual(newer_report.status, "pending")

    @override_settings(
        REPORTS_SAVE_LOCALLY=False, REPORTS_SEND_EMAILS=False, REPORTS_CHUNK_SIZE=100
    )
    @patch("chats.apps.dashboard.tasks.ExcelStorage")
    @patch("chats.apps.api.v1.dashboard.viewsets.ReportFieldsValidatorViewSet")
    def test_process_pending_report_large_dataset(
        self, mock_viewset_class, mock_storage_class
    ):
        report_status = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {"fields": ["is_active"]}, "type": "xlsx"},
        )

        mock_storage = MagicMock()
        mock_storage.listdir.return_value = ([], [])
        mock_storage_class.return_value = mock_storage

        mock_viewset = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 5000
        mock_qs.__iter__ = lambda self: iter(
            [{"is_active": False} for i in range(100)]
        )
        mock_qs.__getitem__ = lambda self, key: [
            {"is_active": False} for i in range(100)
        ]
        mock_viewset._process_model_fields.return_value = {"queryset": mock_qs}
        mock_viewset_class.return_value = mock_viewset

        process_pending_reports()

        report_status.refresh_from_db()
        self.assertEqual(report_status.status, "ready")


class ModelFieldsPresenterTests(TestCase):
    def test_rooms_fields_contains_expected_keys(self):
        models_info = ModelFieldsPresenter.get_models_info()
        rooms_fields = models_info["rooms"]

        expected_fields = {
            "user__first_name",
            "user__last_name",
            "user__email",
            "queue__sector__name",
            "queue__name",
            "is_active",
            "protocol",
            "tags",
            "created_on",
            "ended_at",
            "full_transfer_history",
            "contact__name",
            "contact__uuid",
            "urn",
            "custom_fields",
            "metric__waiting_time",
            "metric__first_response_time",
            "metric__message_response_time",
            "metric__interaction_time",
        }
        self.assertEqual(set(rooms_fields.keys()), expected_fields)

    def test_rooms_fields_does_not_contain_removed_keys(self):
        models_info = ModelFieldsPresenter.get_models_info()
        rooms_fields = models_info["rooms"]

        self.assertNotIn("uuid", rooms_fields)
        self.assertNotIn("transfer_history", rooms_fields)

    def test_rooms_fields_uses_full_transfer_history(self):
        models_info = ModelFieldsPresenter.get_models_info()
        rooms_fields = models_info["rooms"]

        self.assertIn("full_transfer_history", rooms_fields)
        self.assertEqual(rooms_fields["full_transfer_history"]["type"], "JSONField")

    def test_agent_status_logs_contains_expected_keys(self):
        models_info = ModelFieldsPresenter.get_models_info()
        agent_fields = models_info["agent_status_logs"]

        expected_fields = {
            "agent__email",
            "agent__first_name",
            "agent__last_name",
            "project__name",
            "project__uuid",
            "log_date",
            "status_changes",
            "created_on",
        }
        self.assertEqual(set(agent_fields.keys()), expected_fields)

    def test_agent_status_logs_does_not_contain_removed_keys(self):
        models_info = ModelFieldsPresenter.get_models_info()
        agent_fields = models_info["agent_status_logs"]

        self.assertNotIn("uuid", agent_fields)
        self.assertNotIn("modified_on", agent_fields)


class SortFieldsByPriorityTests(TestCase):
    def setUp(self):
        self.viewset = ReportFieldsValidatorViewSet()

    def test_sorts_rooms_fields_in_correct_order(self):
        fields = ["custom_fields", "created_on", "user__first_name", "full_transfer_history"]
        sorted_fields = self.viewset._sort_fields_by_priority(fields)

        self.assertEqual(sorted_fields, [
            "user__first_name",
            "created_on",
            "full_transfer_history",
            "custom_fields",
        ])

    def test_unknown_fields_go_to_end(self):
        fields = ["user__first_name", "some_unknown_field"]
        sorted_fields = self.viewset._sort_fields_by_priority(fields)

        self.assertEqual(sorted_fields[0], "user__first_name")
        self.assertEqual(sorted_fields[-1], "some_unknown_field")

    def test_full_transfer_history_has_priority(self):
        fields = ["urn", "full_transfer_history", "contact__name"]
        sorted_fields = self.viewset._sort_fields_by_priority(fields)

        self.assertLess(
            sorted_fields.index("full_transfer_history"),
            sorted_fields.index("contact__name"),
        )
        self.assertLess(
            sorted_fields.index("full_transfer_history"),
            sorted_fields.index("urn"),
        )


class ApplyRootFiltersTests(TestCase):
    def setUp(self):
        self.viewset = ReportFieldsValidatorViewSet()

    def test_propagates_dates_to_rooms(self):
        fields_config = {
            "start_date": "2026-04-14",
            "end_date": "2026-05-13",
            "rooms": {"fields": ["is_active"]},
        }
        self.viewset._apply_root_filters_to_rooms(fields_config, dict(fields_config))

        self.assertEqual(fields_config["rooms"]["start_date"], "2026-04-14")
        self.assertEqual(fields_config["rooms"]["end_date"], "2026-05-13")
        self.assertNotIn("start_date", fields_config)
        self.assertNotIn("end_date", fields_config)

    def test_propagates_dates_to_agent_status_logs(self):
        fields_config = {
            "start_date": "2026-04-14",
            "end_date": "2026-05-13",
            "agent_status_logs": {"fields": ["agent__email", "log_date"]},
        }
        self.viewset._apply_root_filters_to_rooms(fields_config, dict(fields_config))

        self.assertEqual(
            fields_config["agent_status_logs"]["start_date"], "2026-04-14"
        )
        self.assertEqual(
            fields_config["agent_status_logs"]["end_date"], "2026-05-13"
        )
        self.assertNotIn("start_date", fields_config)
        self.assertNotIn("end_date", fields_config)

    def test_propagates_dates_to_both_models(self):
        fields_config = {
            "start_date": "2026-04-14",
            "end_date": "2026-05-13",
            "rooms": {"fields": ["is_active"]},
            "agent_status_logs": {"fields": ["agent__email"]},
        }
        self.viewset._apply_root_filters_to_rooms(fields_config, dict(fields_config))

        self.assertEqual(fields_config["rooms"]["start_date"], "2026-04-14")
        self.assertEqual(fields_config["rooms"]["end_date"], "2026-05-13")
        self.assertEqual(
            fields_config["agent_status_logs"]["start_date"], "2026-04-14"
        )
        self.assertEqual(
            fields_config["agent_status_logs"]["end_date"], "2026-05-13"
        )

    def test_does_not_overwrite_existing_nested_dates(self):
        fields_config = {
            "start_date": "2026-04-14",
            "end_date": "2026-05-13",
            "agent_status_logs": {
                "fields": ["agent__email"],
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
            },
        }
        self.viewset._apply_root_filters_to_rooms(fields_config, dict(fields_config))

        self.assertEqual(
            fields_config["agent_status_logs"]["start_date"], "2026-01-01"
        )
        self.assertEqual(
            fields_config["agent_status_logs"]["end_date"], "2026-01-31"
        )

    def test_propagates_root_agents_to_agent_status_logs(self):
        fields_config = {
            "agents": ["uuid-1", "uuid-2"],
            "agent_status_logs": {"fields": ["agent__email"]},
        }
        request_data = {"agents": ["uuid-1", "uuid-2"]}
        self.viewset._apply_root_filters_to_rooms(fields_config, request_data)

        self.assertEqual(
            fields_config["agent_status_logs"]["agents"], ["uuid-1", "uuid-2"]
        )

    def test_propagates_root_users_emails_to_rooms_and_agent_status_logs(self):
        users_filter = {
            "emails": ["agent1@test.com", "agent2@test.com"],
            "fields": [],
        }
        fields_config = {
            "users": users_filter,
            "rooms": {"fields": ["is_active"]},
            "agent_status_logs": {"fields": ["agent__email"]},
        }
        request_data = {
            "users": users_filter,
            "rooms": {"fields": ["is_active"]},
            "agent_status_logs": {"fields": ["agent__email"]},
        }
        self.viewset._apply_root_filters_to_rooms(fields_config, request_data)

        self.assertEqual(fields_config["rooms"]["agents"], users_filter)
        self.assertEqual(
            fields_config["agent_status_logs"]["agents"], users_filter
        )

    def test_users_takes_precedence_over_agents(self):
        users_filter = {"emails": ["user@test.com"], "fields": []}
        fields_config = {
            "users": users_filter,
            "agents": ["legacy@test.com"],
            "rooms": {"fields": ["is_active"]},
        }
        request_data = {
            "users": users_filter,
            "agents": ["legacy@test.com"],
        }
        self.viewset._apply_root_filters_to_rooms(fields_config, request_data)

        self.assertEqual(fields_config["rooms"]["agents"], users_filter)

    def test_propagates_root_sectors_and_queues_to_rooms(self):
        sectors_filter = {"uuids": ["sector-uuid-1"], "fields": []}
        queues_filter = {"uuids": ["queue-uuid-1"], "fields": []}
        fields_config = {
            "sectors": sectors_filter,
            "queues": queues_filter,
            "rooms": {"fields": ["is_active"]},
        }
        request_data = {
            "sectors": sectors_filter,
            "queues": queues_filter,
            "rooms": {"fields": ["is_active"]},
        }
        self.viewset._apply_root_filters_to_rooms(fields_config, request_data)

        self.assertEqual(fields_config["rooms"]["sectors"], sectors_filter)
        self.assertEqual(fields_config["rooms"]["queues"], queues_filter)

    def test_propagates_root_sector_tags_to_rooms(self):
        sector_tags_filter = {"uuids": ["tag-uuid-1"], "fields": []}
        fields_config = {
            "sector_tags": sector_tags_filter,
            "rooms": {"fields": ["is_active"]},
        }
        request_data = {
            "sector_tags": sector_tags_filter,
            "rooms": {"fields": ["is_active"]},
        }
        self.viewset._apply_root_filters_to_rooms(fields_config, request_data)

        self.assertEqual(fields_config["rooms"]["tags"], sector_tags_filter)

    def test_all_filter_does_not_restrict_sectors(self):
        result = self.viewset._normalize_filter_value(
            {"uuids": ["__all__"], "fields": []}
        )
        self.assertEqual(result, [])

    def test_no_dates_in_root_leaves_nested_untouched(self):
        fields_config = {
            "agent_status_logs": {"fields": ["agent__email"]},
        }
        self.viewset._apply_root_filters_to_rooms(fields_config, dict(fields_config))

        self.assertNotIn("start_date", fields_config["agent_status_logs"])
        self.assertNotIn("end_date", fields_config["agent_status_logs"])


class NormalizeFilterValueTests(TestCase):
    def setUp(self):
        self.viewset = ReportFieldsValidatorViewSet()

    def test_normalize_emails_dict(self):
        result = self.viewset._normalize_filter_value(
            {"emails": ["Agent1@Test.COM", " agent2@test.com "], "fields": []}
        )
        self.assertEqual(result, ["agent1@test.com", "agent2@test.com"])

    def test_normalize_emails_all_returns_empty(self):
        result = self.viewset._normalize_filter_value(
            {"emails": ["__all__"], "fields": []}
        )
        self.assertEqual(result, [])

    def test_normalize_uuids_still_works(self):
        result = self.viewset._normalize_filter_value(
            {"uuids": ["uuid-1", "uuid-2"], "fields": []}
        )
        self.assertEqual(result, ["uuid-1", "uuid-2"])


class ApplyEntityFiltersByEmailTests(TestCase):
    def setUp(self):
        self.viewset = ReportFieldsValidatorViewSet()

    def test_rooms_filter_uses_user_email(self):
        queryset = Mock()
        queryset.filter.return_value = queryset

        result = self.viewset._apply_entity_filters(
            queryset,
            {"agents": {"emails": ["agent@test.com"], "fields": []}},
        )

        queryset.filter.assert_called_once_with(
            user__email__in=["agent@test.com"]
        )
        self.assertEqual(result, queryset)

    def test_rooms_filter_sectors_queues_and_tags_by_uuid(self):
        queryset = Mock()
        queryset.filter.return_value = queryset

        result = self.viewset._apply_entity_filters(
            queryset,
            {
                "sectors": {"uuids": ["sector-1"], "fields": []},
                "queues": {"uuids": ["queue-1"], "fields": []},
                "tags": {"uuids": ["tag-1"], "fields": []},
            },
        )

        self.assertEqual(queryset.filter.call_count, 3)
        queryset.filter.assert_any_call(queue__sector__uuid__in=["sector-1"])
        queryset.filter.assert_any_call(queue__uuid__in=["queue-1"])
        queryset.filter.assert_any_call(tags__uuid__in=["tag-1"])
        self.assertEqual(result, queryset)

    def test_all_sectors_does_not_call_sector_filter(self):
        queryset = Mock()
        queryset.filter.return_value = queryset

        result = self.viewset._apply_entity_filters(
            queryset,
            {"sectors": {"uuids": ["__all__"], "fields": []}},
        )

        queryset.filter.assert_not_called()
        self.assertEqual(result, queryset)

    def test_agent_status_logs_filter_uses_agent_email(self):
        queryset = Mock()
        queryset.filter.return_value = queryset
        project = Mock()
        project.timezone = "UTC"

        result = self.viewset._apply_agent_status_logs_filters(
            queryset,
            {"agents": {"emails": ["agent@test.com"], "fields": []}},
            project,
        )

        queryset.filter.assert_called_once_with(
            agent__email__in=["agent@test.com"]
        )
        self.assertEqual(result, queryset)
