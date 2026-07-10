from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.v1.dashboard.viewsets import ReportFieldsValidatorViewSet
from chats.apps.projects.models import Project, ProjectPermission


User = get_user_model()


class DashboardLiveViewsetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="dash@example.com", password="x"
        )
        self.project = Project.objects.create(name="Dashboard Project")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.client.force_authenticate(user=self.user)
        self.base = f"/v1/dashboard/{self.project.uuid}"

    @patch("chats.apps.api.v1.dashboard.viewsets.RoomsDataService")
    def test_general(self, mock_service_cls):
        mock_service_cls.return_value.get_rooms_data.return_value = [
            {"active_chats": 1}
        ]
        response = self.client.get(f"{self.base}/general/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rooms_data"], [{"active_chats": 1}])
        mock_service_cls.return_value.get_rooms_data.assert_called_once()

    @patch("chats.apps.api.v1.dashboard.viewsets.AgentsService")
    def test_agent(self, mock_service_cls):
        mock_service_cls.return_value.get_agents_data.return_value = [
            {
                "first_name": "A",
                "last_name": "B",
                "email": "a@example.com",
                "agent_status": "ONLINE",
                "closed_rooms": 1,
                "opened_rooms": 2,
            }
        ]
        response = self.client.get(f"{self.base}/agent/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["project_agents"]), 1)
        self.assertEqual(response.data["project_agents"][0]["email"], "a@example.com")

    @patch("chats.apps.api.v1.dashboard.viewsets.SectorService")
    def test_division(self, mock_service_cls):
        mock_service_cls.return_value.get_sector_data.return_value = [
            {
                "uuid": "sec-1",
                "name": "Sector",
                "waiting_time": 10,
                "response_time": 20,
                "interact_time": 30,
            }
        ]
        response = self.client.get(f"{self.base}/division/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["sectors"][0]["name"], "Sector")

    @patch("chats.apps.api.v1.dashboard.viewsets.RawDataService")
    def test_raw_data(self, mock_service_cls):
        mock_service_cls.return_value.get_raw_data.return_value = {
            "raw_data": [
                {
                    "active_rooms": 1,
                    "closed_rooms": 2,
                    "transfer_count": 0,
                    "queue_rooms": 3,
                }
            ]
        }
        response = self.client.get(f"{self.base}/raw_data/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["raw_data"][0]["active_rooms"], 1)

    @patch("chats.apps.api.v1.dashboard.viewsets.TimeMetricsService")
    def test_time_metrics(self, mock_service_cls):
        mock_service_cls.return_value.get_time_metrics.return_value = {
            "average_waiting_time": 5
        }
        response = self.client.get(f"{self.base}/time_metrics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["average_waiting_time"], 5)

    @patch("chats.apps.api.v1.dashboard.viewsets.TimeMetricsService")
    def test_time_metrics_for_analysis(self, mock_service_cls):
        mock_service_cls.return_value.get_time_metrics_for_analysis.return_value = {
            "metrics": []
        }
        response = self.client.get(f"{self.base}/time_metrics_for_analysis/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["metrics"], [])


class ModelFieldsViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="fields@example.com", password="x"
        )
        self.client.force_authenticate(user=self.user)

    @patch(
        "chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter.get_models_info",
        return_value={"rooms": {"fields": ["uuid"]}},
    )
    def test_get_model_fields(self, mock_info):
        response = self.client.get("/v1/model-fields/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rooms"]["fields"], ["uuid"])
        mock_info.assert_called_once()


class ReportFieldsValidatorHelpersTests(APITestCase):
    def setUp(self):
        self.view = ReportFieldsValidatorViewSet()

    def test_estimate_execution_time_zero(self):
        self.assertEqual(self.view._estimate_execution_time(0), 30)

    def test_estimate_execution_time_large(self):
        # Cap at 600
        self.assertEqual(self.view._estimate_execution_time(1_000_000), 600)

    def test_is_true(self):
        self.assertTrue(self.view._is_true(True))
        self.assertTrue(self.view._is_true("true"))
        self.assertTrue(self.view._is_true("1"))
        self.assertFalse(self.view._is_true(False))
        self.assertFalse(self.view._is_true("false"))

    def test_normalize_list_filter_all(self):
        self.assertEqual(self.view._normalize_list_filter(["__all__"]), [])

    def test_normalize_list_filter_dicts(self):
        self.assertEqual(
            self.view._normalize_list_filter([{"uuid": "a"}, {"value": "b"}]),
            ["a", "b"],
        )

    def test_normalize_dict_filter_uuids(self):
        self.assertEqual(
            self.view._normalize_dict_filter({"uuids": ["u1", "u2"]}),
            ["u1", "u2"],
        )

    def test_normalize_dict_filter_uuid(self):
        self.assertEqual(self.view._normalize_dict_filter({"uuid": "u1"}), ["u1"])

    def test_normalize_dict_filter_value(self):
        self.assertEqual(self.view._normalize_dict_filter({"value": "v"}), ["v"])

    def test_normalize_filter_value_none(self):
        self.assertEqual(self.view._normalize_filter_value(None), [])

    def test_normalize_filter_value_string(self):
        self.assertEqual(self.view._normalize_filter_value("x"), ["x"])
        self.assertEqual(self.view._normalize_filter_value("__all__"), [])

    def test_group_duplicate_records_empty(self):
        self.assertEqual(self.view._group_duplicate_records([]), [])

    def test_group_duplicate_records_no_lookups(self):
        data = [{"uuid": "1", "name": "a"}]
        self.assertEqual(self.view._group_duplicate_records(data), data)

    def test_group_duplicate_records_with_lookups(self):
        raw = [
            {"uuid": "1", "tags__name": "t1"},
            {"uuid": "1", "tags__name": "t2"},
            {"uuid": "2", "tags__name": "t3"},
        ]
        result = self.view._group_duplicate_records(raw)
        by_uuid = {row["uuid"]: row for row in result}
        self.assertEqual(sorted(by_uuid["1"]["tags__name"]), ["t1", "t2"])
        self.assertEqual(by_uuid["2"]["tags__name"], "t3")

    @patch(
        "chats.apps.api.v1.dashboard.viewsets.ModelFieldsPresenter.get_models_info",
        return_value={"rooms": {}, "agent_status_logs": {}},
    )
    def test_filter_valid_models(self, _mock_info):
        result = self.view._filter_valid_models(
            {"rooms": {"fields": ["uuid"]}, "unknown": {"fields": []}}
        )
        self.assertIn("rooms", result)
        self.assertNotIn("unknown", result)
