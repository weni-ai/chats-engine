from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.test import force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.viewsets import ReportFieldsValidatorViewSet
from chats.apps.dashboard.models import ReportStatus
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class ReportFieldsValidatorPostTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(email="agent@test.com")
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Support",
            project=self.project,
            rooms_limit=5,
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        ProjectPermission.objects.create(project=self.project, user=self.user, role=1)
        self.view = ReportFieldsValidatorViewSet.as_view()

    def _make_post_request(self, data):
        request = self.factory.post("/report/", data=data, content_type="application/json")
        force_authenticate(request, user=self.user)
        return self.view(request)

    def test_post_requires_project_uuid(self):
        response = self._make_post_request({})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_returns_404_for_nonexistent_project(self):
        response = self._make_post_request({
            "project_uuid": "00000000-0000-0000-0000-000000000000"
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_returns_error_when_report_in_progress(self):
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="pending",
            fields_config={"rooms": {}},
        )
        
        response = self._make_post_request({
            "project_uuid": str(self.project.uuid)
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["code"], "max_report_limit")

    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_creates_report_status(self, mock_presenter, mock_process, mock_estimate):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
        }
        mock_qs = MagicMock()
        mock_qs.count.return_value = 10
        mock_process.return_value = {"queryset": mock_qs}
        mock_estimate.return_value = 60
        
        response = self._make_post_request({
            "project_uuid": str(self.project.uuid),
            "rooms": {"fields": ["uuid"]},
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("report_uuid", response.data)
        self.assertTrue(
            ReportStatus.objects.filter(project=self.project, status="pending").exists()
        )

    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_returns_estimated_time(self, mock_presenter, mock_process, mock_estimate):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
        }
        mock_qs = MagicMock()
        mock_qs.count.return_value = 10
        mock_process.return_value = {"queryset": mock_qs}
        mock_estimate.return_value = 120
        
        response = self._make_post_request({
            "project_uuid": str(self.project.uuid),
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("time_request", response.data)

    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_handles_open_chats_filter(self, mock_presenter, mock_process, mock_estimate):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
        }
        mock_qs = MagicMock()
        mock_qs.count.return_value = 5
        mock_process.return_value = {"queryset": mock_qs}
        mock_estimate.return_value = 60
        
        response = self._make_post_request({
            "project_uuid": str(self.project.uuid),
            "open_chats": True,
            "closed_chats": False,
            "rooms": {},
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report = ReportStatus.objects.get(project=self.project)
        self.assertTrue(report.fields_config["rooms"]["open_chats"])

    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_applies_root_date_filters_to_rooms(self, mock_presenter, mock_process, mock_estimate):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
        }
        mock_qs = MagicMock()
        mock_qs.count.return_value = 5
        mock_process.return_value = {"queryset": mock_qs}
        mock_estimate.return_value = 60
        
        response = self._make_post_request({
            "project_uuid": str(self.project.uuid),
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "rooms": {},
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report = ReportStatus.objects.get(project=self.project)
        self.assertEqual(report.fields_config["rooms"]["start_date"], "2025-01-01")
        self.assertEqual(report.fields_config["rooms"]["end_date"], "2025-12-31")

    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_saves_file_type_in_config(self, mock_presenter, mock_process, mock_estimate):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
        }
        mock_qs = MagicMock()
        mock_qs.count.return_value = 5
        mock_process.return_value = {"queryset": mock_qs}
        mock_estimate.return_value = 60
        
        response = self._make_post_request({
            "project_uuid": str(self.project.uuid),
            "type": "csv",
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report = ReportStatus.objects.get(project=self.project)
        self.assertEqual(report.fields_config["type"], "csv")

    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_handles_agents_filter(self, mock_presenter, mock_process, mock_estimate):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
        }
        mock_qs = MagicMock()
        mock_qs.count.return_value = 5
        mock_process.return_value = {"queryset": mock_qs}
        mock_estimate.return_value = 60
        
        agent_uuid = "11111111-1111-1111-1111-111111111111"
        response = self._make_post_request({
            "project_uuid": str(self.project.uuid),
            "agents": [agent_uuid],
            "rooms": {},
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report = ReportStatus.objects.get(project=self.project)
        self.assertEqual(report.fields_config["rooms"]["agents"], [agent_uuid])

    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_handles_tags_filter(self, mock_presenter, mock_process, mock_estimate):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
        }
        mock_qs = MagicMock()
        mock_qs.count.return_value = 5
        mock_process.return_value = {"queryset": mock_qs}
        mock_estimate.return_value = 60
        
        tag_uuid = "22222222-2222-2222-2222-222222222222"
        response = self._make_post_request({
            "project_uuid": str(self.project.uuid),
            "tags": [tag_uuid],
            "rooms": {},
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report = ReportStatus.objects.get(project=self.project)
        self.assertEqual(report.fields_config["rooms"]["tags"], [tag_uuid])

    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_defaults_to_empty_rooms_when_no_valid_model(self, mock_presenter, mock_process, mock_estimate):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
        }
        mock_qs = MagicMock()
        mock_qs.count.return_value = 0
        mock_process.return_value = {"queryset": mock_qs}
        mock_estimate.return_value = 60
        
        response = self._make_post_request({
            "project_uuid": str(self.project.uuid),
            "invalid_model": {"fields": ["x"]},
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report = ReportStatus.objects.get(project=self.project)
        self.assertIn("rooms", report.fields_config)

    @patch.object(ReportFieldsValidatorViewSet, "_estimate_execution_time")
    @patch.object(ReportFieldsValidatorViewSet, "_get_rooms_queryset")
    @patch.object(ReportFieldsValidatorViewSet, "_process_model_fields")
    @patch("chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter")
    def test_post_handles_queryset_count_exception(self, mock_presenter, mock_process, mock_qs_method, mock_estimate):
        mock_presenter.get_models_info.return_value = {
            "rooms": {"fields": ["uuid"]},
        }
        mock_process.side_effect = Exception("DB error")
        mock_fallback_qs = MagicMock()
        mock_fallback_qs.count.return_value = 10
        mock_qs_method.return_value = mock_fallback_qs
        mock_estimate.return_value = 60
        
        response = self._make_post_request({
            "project_uuid": str(self.project.uuid),
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ReportFieldsValidatorGetTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(email="agent@test.com")
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        ProjectPermission.objects.create(project=self.project, user=self.user, role=1)
        self.view = ReportFieldsValidatorViewSet.as_view()

    def _make_get_request(self, params):
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        request = self.factory.get(f"/report/?{query_string}")
        force_authenticate(request, user=self.user)
        return self.view(request)

    def test_get_requires_project_uuid(self):
        response = self._make_get_request({})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_returns_ready_status_when_no_completed_export(self):
        response = self._make_get_request({
            "project_uuid": str(self.project.uuid)
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ready")
        self.assertIsNone(response.data["email"])

    def test_get_returns_latest_report_status(self):
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            status="ready",
            fields_config={"rooms": {}},
        )
        
        response = self._make_get_request({
            "project_uuid": str(self.project.uuid)
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ready")
        self.assertEqual(response.data["email"], self.user.email)
