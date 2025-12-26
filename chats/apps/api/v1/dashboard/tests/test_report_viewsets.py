from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.viewsets import ReportFieldsValidatorViewSet
from chats.apps.dashboard.models import ReportStatus
from chats.apps.projects.models import Project


class GroupDuplicateRecordsTests(TestCase):
    def setUp(self):
        self.viewset = ReportFieldsValidatorViewSet()

    def test_group_duplicate_records_empty_data(self):
        result = self.viewset._group_duplicate_records([])
        self.assertEqual(result, [])

    def test_group_duplicate_records_none_data(self):
        result = self.viewset._group_duplicate_records(None)
        self.assertEqual(result, [])

    def test_group_duplicate_records_no_lookups(self):
        raw_data = [
            {"uuid": "1", "name": "Test 1"},
            {"uuid": "2", "name": "Test 2"},
        ]
        result = self.viewset._group_duplicate_records(raw_data)
        self.assertEqual(result, raw_data)

    def test_group_duplicate_records_no_group_fields(self):
        raw_data = [{"related__field": "value1"}]
        result = self.viewset._group_duplicate_records(raw_data)
        self.assertEqual(result, raw_data)

    def test_group_duplicate_records_with_lookups(self):
        raw_data = [
            {"uuid": "1", "name": "Test", "tags__name": "tag1"},
            {"uuid": "1", "name": "Test", "tags__name": "tag2"},
            {"uuid": "1", "name": "Test", "tags__name": "tag3"},
        ]
        result = self.viewset._group_duplicate_records(raw_data)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["uuid"], "1")
        self.assertEqual(result[0]["name"], "Test")
        self.assertEqual(sorted(result[0]["tags__name"]), ["tag1", "tag2", "tag3"])

    def test_group_duplicate_records_with_multiple_groups(self):
        raw_data = [
            {"uuid": "1", "name": "Test 1", "tags__name": "tag1"},
            {"uuid": "1", "name": "Test 1", "tags__name": "tag2"},
            {"uuid": "2", "name": "Test 2", "tags__name": "tag3"},
        ]
        result = self.viewset._group_duplicate_records(raw_data)

        self.assertEqual(len(result), 2)

    def test_group_duplicate_records_removes_duplicate_values(self):
        raw_data = [
            {"uuid": "1", "tags__name": "tag1"},
            {"uuid": "1", "tags__name": "tag1"},
            {"uuid": "1", "tags__name": "tag2"},
        ]
        result = self.viewset._group_duplicate_records(raw_data)

        self.assertEqual(len(result), 1)
        self.assertEqual(sorted(result[0]["tags__name"]), ["tag1", "tag2"])

    def test_group_duplicate_records_single_value_unwrapped(self):
        raw_data = [{"uuid": "1", "tags__name": "tag1"}]
        result = self.viewset._group_duplicate_records(raw_data)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tags__name"], "tag1")

    def test_group_duplicate_records_empty_values_become_none(self):
        raw_data = [{"uuid": "1", "tags__name": None}]
        result = self.viewset._group_duplicate_records(raw_data)

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["tags__name"])

    def test_group_duplicate_records_with_multiple_lookup_fields(self):
        raw_data = [
            {"uuid": "1", "tags__name": "tag1", "user__email": "user1@test.com"},
            {"uuid": "1", "tags__name": "tag2", "user__email": "user1@test.com"},
        ]
        result = self.viewset._group_duplicate_records(raw_data)

        self.assertEqual(len(result), 1)
        self.assertEqual(sorted(result[0]["tags__name"]), ["tag1", "tag2"])
        self.assertEqual(result[0]["user__email"], "user1@test.com")


class ReportFieldsValidatorViewSetPostTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.user = User.objects.create_user(
            email="test@test.com", first_name="Test", last_name="User"
        )
        self.viewset = ReportFieldsValidatorViewSet()

    def test_post_without_project_uuid_raises_error(self):
        request = MagicMock()
        request.data = {}

        with self.assertRaises(ValidationError):
            self.viewset.post(request)

    def test_post_with_invalid_project_uuid_raises_404(self):
        request = MagicMock()
        request.data = {"project_uuid": "00000000-0000-0000-0000-000000000000"}

        from django.http import Http404

        with self.assertRaises(Http404):
            self.viewset.post(request)

    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch.object(ReportFieldsValidatorViewSet, "_get_rooms_queryset")
    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_with_active_report_returns_error(
        self, mock_presenter, mock_estimate, mock_get_rooms, mock_process
    ):
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={},
        )

        request = MagicMock()
        request.data = {"project_uuid": str(self.project.uuid)}
        request.user = self.user

        response = self.viewset.post(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "max_report_limit")

    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch.object(ReportFieldsValidatorViewSet, "_get_rooms_queryset")
    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_creates_report_status(
        self, mock_presenter, mock_estimate, mock_get_rooms, mock_process
    ):
        mock_presenter.get_models_info.return_value = {"rooms": {"fields": ["uuid"]}}
        mock_process.return_value = {
            "queryset": MagicMock(count=MagicMock(return_value=10))
        }
        mock_estimate.return_value = 60

        request = MagicMock()
        request.data = {
            "project_uuid": str(self.project.uuid),
            "rooms": {"fields": ["uuid"]},
        }
        request.user = self.user

        response = self.viewset.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("report_uuid", response.data)
        self.assertIn("time_request", response.data)

    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch.object(ReportFieldsValidatorViewSet, "_get_rooms_queryset")
    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_handles_open_chats_filter(
        self, mock_presenter, mock_estimate, mock_get_rooms, mock_process
    ):
        mock_presenter.get_models_info.return_value = {"rooms": {"fields": ["uuid"]}}
        mock_process.return_value = {
            "queryset": MagicMock(count=MagicMock(return_value=10))
        }
        mock_estimate.return_value = 60

        request = MagicMock()
        request.data = {
            "project_uuid": str(self.project.uuid),
            "rooms": {"fields": ["uuid"]},
            "open_chats": True,
        }
        request.user = self.user

        response = self.viewset.post(request)

        self.assertEqual(response.status_code, 200)

    @patch.object(ReportFieldsValidatorViewSet, "_get_rooms_queryset")
    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_defaults_to_empty_rooms_when_no_valid_model(
        self, mock_presenter, mock_estimate, mock_get_rooms
    ):
        mock_presenter.get_models_info.return_value = {"rooms": {"fields": ["uuid"]}}
        mock_get_rooms.return_value = MagicMock(count=MagicMock(return_value=0))
        mock_estimate.return_value = 60

        request = MagicMock()
        request.data = {
            "project_uuid": str(self.project.uuid),
            "invalid_model": {"fields": ["uuid"]},
        }
        request.user = self.user

        response = self.viewset.post(request)

        self.assertEqual(response.status_code, 200)


class ReportFieldsValidatorViewSetGetTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.user = User.objects.create_user(
            email="test@test.com", first_name="Test", last_name="User"
        )
        self.viewset = ReportFieldsValidatorViewSet()

    def test_get_without_project_uuid_raises_error(self):
        request = MagicMock()
        request.query_params = {}

        with self.assertRaises(ValidationError):
            self.viewset.get(request)

    def test_get_with_no_completed_export(self):
        request = MagicMock()
        request.query_params = {"project_uuid": str(self.project.uuid)}

        response = self.viewset.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ready")
        self.assertIsNone(response.data["email"])
        self.assertIsNone(response.data["report_uuid"])

    def test_get_with_completed_export(self):
        report = ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="ready",
            fields_config={},
        )

        request = MagicMock()
        request.query_params = {"project_uuid": str(self.project.uuid)}

        response = self.viewset.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ready")
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["report_uuid"], str(report.uuid))
