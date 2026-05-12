from unittest.mock import MagicMock, patch

from django.db.models import Q
from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v2.internal.dashboard.usecases.agents import (
    InternalDashboardAgentsUsecase,
)
from chats.apps.api.v2.internal.dashboard.usecases.custom_status_by_agent import (
    InternalDashboardCustomStatusByAgentUsecase,
)
from chats.apps.projects.models.models import (
    CustomStatus,
    CustomStatusType,
    Project,
)

USECASE_MODULE = "chats.apps.api.v2.internal.dashboard.usecases.agents"


class InternalDashboardAgentsUsecaseTests(TestCase):
    def setUp(self):
        self.usecase = InternalDashboardAgentsUsecase()
        self.project = Project.objects.create(
            name="Test Project",
            timezone="America/Sao_Paulo",
        )

    def _mock_agents_service(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_queryset = MagicMock()
        mock_service.get_agents_data.return_value = mock_queryset
        return mock_service, mock_queryset

    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_builds_filters_dto(self, mock_service_cls):
        mock_service, _ = self._mock_agents_service(mock_service_cls)

        filters = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "agent": "agent@test.com",
            "sector": ["sector-uuid"],
            "tag": ["tag1"],
            "queue": ["queue-uuid"],
            "user_request": "user@test.com",
            "ordering": "status",
        }

        self.usecase.execute(self.project, filters)

        mock_service.get_agents_data.assert_called_once()
        dto, project = mock_service.get_agents_data.call_args[0]
        kwargs = mock_service.get_agents_data.call_args[1]

        self.assertIsInstance(dto, Filters)
        self.assertEqual(dto.start_date, "2024-01-01")
        self.assertEqual(dto.end_date, "2024-01-31")
        self.assertEqual(dto.agent, "agent@test.com")
        self.assertEqual(dto.sector, ["sector-uuid"])
        self.assertEqual(dto.tag, ["tag1"])
        self.assertEqual(dto.queues, ["queue-uuid"])
        self.assertEqual(dto.user_request, "user@test.com")
        self.assertEqual(dto.ordering, "status")
        self.assertEqual(project, self.project)
        self.assertTrue(kwargs.get("include_removed"))

    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_with_empty_filters(self, mock_service_cls):
        mock_service, _ = self._mock_agents_service(mock_service_cls)

        self.usecase.execute(self.project, {})

        dto = mock_service.get_agents_data.call_args[0][0]
        kwargs = mock_service.get_agents_data.call_args[1]

        self.assertIsNone(dto.start_date)
        self.assertIsNone(dto.end_date)
        self.assertIsNone(dto.agent)
        self.assertIsNone(dto.sector)
        self.assertIsNone(dto.tag)
        self.assertIsNone(dto.queues)
        self.assertEqual(dto.user_request, "")
        self.assertIsNone(dto.ordering)
        self.assertTrue(kwargs.get("include_removed"))

    @patch(f"{USECASE_MODULE}.should_exclude_admin_domains")
    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_computes_is_weni_admin_from_user_request(
        self, mock_service_cls, mock_exclude
    ):
        mock_service, _ = self._mock_agents_service(mock_service_cls)
        mock_exclude.return_value = True

        self.usecase.execute(self.project, {"user_request": "admin@weni.ai"})

        mock_exclude.assert_called_once_with("admin@weni.ai")
        dto = mock_service.get_agents_data.call_args[0][0]
        self.assertTrue(dto.is_weni_admin)

    @patch(f"{USECASE_MODULE}.should_exclude_admin_domains")
    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_is_weni_admin_false_for_regular_user(
        self, mock_service_cls, mock_exclude
    ):
        mock_service, _ = self._mock_agents_service(mock_service_cls)
        mock_exclude.return_value = False

        self.usecase.execute(self.project, {"user_request": "user@company.com"})

        mock_exclude.assert_called_once_with("user@company.com")
        dto = mock_service.get_agents_data.call_args[0][0]
        self.assertFalse(dto.is_weni_admin)

    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_no_post_filters_returns_service_data(self, mock_service_cls):
        _, mock_queryset = self._mock_agents_service(mock_service_cls)

        result = self.usecase.execute(self.project, {})

        mock_queryset.filter.assert_not_called()
        self.assertEqual(result, mock_queryset)

    @patch(f"{USECASE_MODULE}._build_status_filter")
    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_applies_status_filter(self, mock_service_cls, mock_build_status):
        _, mock_queryset = self._mock_agents_service(mock_service_cls)
        mock_filtered = MagicMock()
        mock_queryset.filter.return_value = mock_filtered

        status_q = Q(status="ONLINE")
        mock_build_status.return_value = status_q

        result = self.usecase.execute(self.project, {"status": ["online"]})

        mock_build_status.assert_called_once_with(["online"])
        mock_queryset.filter.assert_called_once()
        self.assertEqual(result, mock_filtered)

    @patch(f"{USECASE_MODULE}._build_status_filter")
    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_skips_filter_when_build_status_returns_none(
        self, mock_service_cls, mock_build_status
    ):
        _, mock_queryset = self._mock_agents_service(mock_service_cls)
        mock_build_status.return_value = None

        result = self.usecase.execute(self.project, {"status": []})

        mock_queryset.filter.assert_not_called()
        self.assertEqual(result, mock_queryset)

    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_applies_custom_status_filter(self, mock_service_cls):
        _, mock_queryset = self._mock_agents_service(mock_service_cls)
        mock_filtered = MagicMock()
        mock_queryset.filter.return_value = mock_filtered

        user = User.objects.create(email="agent@test.com")
        status_type = CustomStatusType.objects.create(
            name="Pausa", project=self.project
        )
        CustomStatus.objects.create(
            user=user,
            status_type=status_type,
            is_active=True,
            project=self.project,
        )

        result = self.usecase.execute(self.project, {"custom_status": ["Pausa"]})

        mock_queryset.filter.assert_called_once()
        filter_arg = mock_queryset.filter.call_args[0][0]
        self.assertIn("email__in", str(filter_arg))
        self.assertEqual(result, mock_filtered)

    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_custom_status_no_matches_filters_empty(self, mock_service_cls):
        _, mock_queryset = self._mock_agents_service(mock_service_cls)
        mock_filtered = MagicMock()
        mock_queryset.filter.return_value = mock_filtered

        result = self.usecase.execute(self.project, {"custom_status": ["NonExistent"]})

        mock_queryset.filter.assert_called_once()
        filter_arg = mock_queryset.filter.call_args[0][0]
        self.assertIn("pk__in", str(filter_arg))
        self.assertEqual(result, mock_filtered)

    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_ignores_inactive_custom_statuses(self, mock_service_cls):
        _, mock_queryset = self._mock_agents_service(mock_service_cls)
        mock_filtered = MagicMock()
        mock_queryset.filter.return_value = mock_filtered

        user = User.objects.create(email="agent@test.com")
        status_type = CustomStatusType.objects.create(
            name="Pausa", project=self.project
        )
        CustomStatus.objects.create(
            user=user,
            status_type=status_type,
            is_active=False,
            project=self.project,
        )

        self.usecase.execute(self.project, {"custom_status": ["Pausa"]})

        filter_arg = mock_queryset.filter.call_args[0][0]
        self.assertIn("pk__in", str(filter_arg))

    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_custom_status_scoped_to_project(self, mock_service_cls):
        _, mock_queryset = self._mock_agents_service(mock_service_cls)
        mock_filtered = MagicMock()
        mock_queryset.filter.return_value = mock_filtered

        other_project = Project.objects.create(name="Other Project", timezone="UTC")
        user = User.objects.create(email="agent@test.com")
        status_type = CustomStatusType.objects.create(
            name="Pausa", project=other_project
        )
        CustomStatus.objects.create(
            user=user,
            status_type=status_type,
            is_active=True,
            project=other_project,
        )

        self.usecase.execute(self.project, {"custom_status": ["Pausa"]})

        filter_arg = mock_queryset.filter.call_args[0][0]
        self.assertIn("pk__in", str(filter_arg))

    @patch(f"{USECASE_MODULE}._build_status_filter")
    @patch(f"{USECASE_MODULE}.AgentsService")
    def test_execute_combines_status_and_custom_status_filters(
        self, mock_service_cls, mock_build_status
    ):
        _, mock_queryset = self._mock_agents_service(mock_service_cls)
        mock_filtered = MagicMock()
        mock_queryset.filter.return_value = mock_filtered

        mock_build_status.return_value = Q(status="ONLINE")

        user = User.objects.create(email="agent@test.com")
        status_type = CustomStatusType.objects.create(
            name="Pausa", project=self.project
        )
        CustomStatus.objects.create(
            user=user,
            status_type=status_type,
            is_active=True,
            project=self.project,
        )

        result = self.usecase.execute(
            self.project,
            {"status": ["online"], "custom_status": ["Pausa"]},
        )

        mock_queryset.filter.assert_called_once()
        filter_arg = mock_queryset.filter.call_args[0][0]
        filter_str = str(filter_arg)
        self.assertIn("status", filter_str)
        self.assertIn("email__in", filter_str)
        self.assertEqual(result, mock_filtered)


CUSTOM_STATUS_USECASE_MODULE = (
    "chats.apps.api.v2.internal.dashboard.usecases.custom_status_by_agent"
)


class InternalDashboardCustomStatusByAgentUsecaseTests(TestCase):
    def setUp(self):
        self.usecase = InternalDashboardCustomStatusByAgentUsecase()
        self.project = Project.objects.create(
            name="Test Project",
            timezone="America/Sao_Paulo",
        )

    def _mock_agents_service(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_queryset = MagicMock()
        mock_service.get_agents_custom_status.return_value = mock_queryset
        return mock_service, mock_queryset

    @patch(f"{CUSTOM_STATUS_USECASE_MODULE}.AgentsService")
    def test_execute_builds_filters_dto(self, mock_service_cls):
        mock_service, _ = self._mock_agents_service(mock_service_cls)

        filters = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "agent": "agent@test.com",
            "sector": ["sector-uuid"],
            "tag": ["tag1"],
            "queue": "queue-uuid",
            "user_request": "user@test.com",
            "ordering": "agent",
        }

        self.usecase.execute(self.project, filters)

        mock_service.get_agents_custom_status.assert_called_once()
        dto, project = mock_service.get_agents_custom_status.call_args[0][:2]
        kwargs = mock_service.get_agents_custom_status.call_args[1]

        self.assertIsInstance(dto, Filters)
        self.assertEqual(dto.start_date, "2024-01-01")
        self.assertEqual(dto.end_date, "2024-01-31")
        self.assertEqual(dto.agent, "agent@test.com")
        self.assertEqual(dto.sector, ["sector-uuid"])
        self.assertEqual(dto.tag, ["tag1"])
        self.assertEqual(dto.queue, "queue-uuid")
        self.assertEqual(dto.user_request, "user@test.com")
        self.assertEqual(dto.ordering, "agent")
        self.assertEqual(project, self.project)
        self.assertTrue(kwargs.get("include_removed"))

    @patch(f"{CUSTOM_STATUS_USECASE_MODULE}.AgentsService")
    def test_execute_with_empty_filters(self, mock_service_cls):
        mock_service, _ = self._mock_agents_service(mock_service_cls)

        self.usecase.execute(self.project, {})

        dto = mock_service.get_agents_custom_status.call_args[0][0]
        kwargs = mock_service.get_agents_custom_status.call_args[1]

        self.assertIsNone(dto.start_date)
        self.assertIsNone(dto.end_date)
        self.assertIsNone(dto.agent)
        self.assertIsNone(dto.sector)
        self.assertIsNone(dto.tag)
        self.assertIsNone(dto.queue)
        self.assertEqual(dto.user_request, "")
        self.assertIsNone(dto.ordering)
        self.assertTrue(kwargs.get("include_removed"))

    @patch(f"{CUSTOM_STATUS_USECASE_MODULE}.should_exclude_admin_domains")
    @patch(f"{CUSTOM_STATUS_USECASE_MODULE}.AgentsService")
    def test_execute_computes_is_weni_admin_from_user_request(
        self, mock_service_cls, mock_exclude
    ):
        mock_service, _ = self._mock_agents_service(mock_service_cls)
        mock_exclude.return_value = True

        self.usecase.execute(self.project, {"user_request": "admin@weni.ai"})

        mock_exclude.assert_called_once_with("admin@weni.ai")
        dto = mock_service.get_agents_custom_status.call_args[0][0]
        self.assertTrue(dto.is_weni_admin)

    @patch(f"{CUSTOM_STATUS_USECASE_MODULE}.AgentsService")
    def test_execute_returns_service_data(self, mock_service_cls):
        _, mock_queryset = self._mock_agents_service(mock_service_cls)

        result = self.usecase.execute(self.project, {})

        self.assertEqual(result, mock_queryset)
