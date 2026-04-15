import uuid
from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.tests.decorators import with_project_permission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import GroupSector, Sector, SectorGroupSector


BULK_CREATE_URL = "queue-bulk-create"


def make_flows_response(status_code=201):
    mock = MagicMock()
    mock.status_code = status_code
    mock.content = b""
    return mock


class TestBulkQueueCreateUnauthenticated(APITestCase):
    def test_requires_authentication(self):
        url = reverse(BULK_CREATE_URL)
        response = self.client.post(url, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestBulkQueueCreate(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Test Sector",
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.user = User.objects.create(email="manager@test.com")
        self.client.force_authenticate(user=self.user)

    def _url(self):
        return reverse(BULK_CREATE_URL)

    def _payload(self, queues=None):
        return {
            "sector": str(self.sector.pk),
            "queues": queues
            if queues is not None
            else [{"name": "Fila 1"}, {"name": "Fila 2"}],
        }

    def test_without_project_permission_returns_403(self):
        response = self.client.post(self._url(), data=self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_empty_queues_list_returns_400(self, mock_feature_flag):
        response = self.client.post(
            self._url(),
            data={"sector": str(self.sector.pk), "queues": []},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_duplicate_names_in_request_returns_400(self, mock_feature_flag):
        response = self.client.post(
            self._url(),
            data=self._payload(queues=[{"name": "Fila 1"}, {"name": "Fila 1"}]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_existing_queue_name_in_sector_returns_400(self, mock_feature_flag):
        Queue.objects.create(name="Fila Existente", sector=self.sector)

        response = self.client.post(
            self._url(),
            data=self._payload(
                queues=[{"name": "Fila Existente"}, {"name": "Fila Nova"}]
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=False)
    @with_project_permission()
    def test_queue_limit_active_with_feature_flag_off_returns_400(self, mock_feature_flag):
        response = self.client.post(
            self._url(),
            data=self._payload(
                queues=[
                    {"name": "Fila 1", "queue_limit": {"is_active": True, "limit": 5}}
                ]
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"][0].code, "queue_limit_feature_flag_is_off"
        )

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=False)
    @with_project_permission()
    def test_queue_limit_inactive_with_feature_flag_off_is_allowed(self, mock_feature_flag):
        with override_settings(USE_WENI_FLOWS=False):
            response = self.client.post(
                self._url(),
                data=self._payload(
                    queues=[
                        {
                            "name": "Fila 1",
                            "queue_limit": {"is_active": False, "limit": 5},
                        }
                    ]
                ),
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(USE_WENI_FLOWS=False)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_creates_all_queues_in_db(self, mock_feature_flag):
        response = self.client.post(self._url(), data=self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(Queue.objects.filter(sector=self.sector).count(), 2)

    @override_settings(USE_WENI_FLOWS=False)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_response_contains_expected_fields(self, mock_feature_flag):
        response = self.client.post(self._url(), data=self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for queue_data in response.data:
            self.assertIn("uuid", queue_data)
            self.assertIn("name", queue_data)
            self.assertIn("sector", queue_data)
            self.assertIn("queue_limit", queue_data)

    @override_settings(USE_WENI_FLOWS=False)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_returned_names_match_request(self, mock_feature_flag):
        response = self.client.post(self._url(), data=self._payload(), format="json")

        returned_names = {q["name"] for q in response.data}
        self.assertEqual(returned_names, {"Fila 1", "Fila 2"})

    @override_settings(USE_WENI_FLOWS=False)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_creates_queue_with_all_optional_fields(self, mock_feature_flag):
        payload = {
            "sector": str(self.sector.pk),
            "queues": [
                {
                    "name": "Fila Completa",
                    "default_message": "Olá!",
                    "config": {"key": "value"},
                    "queue_limit": {"limit": 10, "is_active": True},
                }
            ],
        }

        response = self.client.post(self._url(), data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        queue = Queue.objects.get(sector=self.sector, name="Fila Completa")
        self.assertEqual(queue.default_message, "Olá!")
        self.assertEqual(queue.queue_limit, 10)
        self.assertEqual(queue.is_queue_limit_active, True)

    @override_settings(USE_WENI_FLOWS=False)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_creates_queue_without_queue_limit_uses_defaults(self, mock_feature_flag):
        response = self.client.post(
            self._url(),
            data=self._payload(queues=[{"name": "Fila Simples"}]),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        queue = Queue.objects.get(sector=self.sector, name="Fila Simples")
        self.assertIsNone(queue.queue_limit)
        self.assertFalse(queue.is_queue_limit_active)

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @patch("chats.apps.api.v1.queues.viewsets.FlowRESTClient")
    @with_project_permission()
    def test_calls_flows_create_for_each_queue(self, mock_flows_cls, mock_feature_flag):
        mock_flows_cls.return_value.create_queue.return_value = make_flows_response(201)

        response = self.client.post(self._url(), data=self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(mock_flows_cls.return_value.create_queue.call_count, 2)
        self.assertEqual(Queue.objects.filter(sector=self.sector).count(), 2)

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @patch("chats.apps.api.v1.queues.viewsets.FlowRESTClient")
    @with_project_permission()
    def test_flows_failure_on_first_queue_rolls_back_db_and_skips_destroy(
        self, mock_flows_cls, mock_feature_flag
    ):
        mock_flows_cls.return_value.create_queue.return_value = make_flows_response(500)
        mock_flows_cls.return_value.destroy_queue.return_value = make_flows_response(200)

        response = self.client.post(self._url(), data=self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(Queue.objects.filter(sector=self.sector).count(), 0)
        mock_flows_cls.return_value.destroy_queue.assert_not_called()

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @patch("chats.apps.api.v1.queues.viewsets.FlowRESTClient")
    @with_project_permission()
    def test_flows_failure_on_second_queue_rolls_back_db_and_destroys_first(
        self, mock_flows_cls, mock_feature_flag
    ):
        mock_flows_cls.return_value.create_queue.side_effect = [
            make_flows_response(201),
            make_flows_response(500),
        ]
        mock_flows_cls.return_value.destroy_queue.return_value = make_flows_response(200)

        response = self.client.post(self._url(), data=self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(Queue.objects.filter(sector=self.sector).count(), 0)
        self.assertEqual(mock_flows_cls.return_value.destroy_queue.call_count, 1)

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @patch("chats.apps.api.v1.queues.viewsets.FlowRESTClient")
    @with_project_permission()
    def test_flows_calls_include_correct_uuids(self, mock_flows_cls, mock_feature_flag):
        mock_flows_cls.return_value.create_queue.return_value = make_flows_response(201)

        self.client.post(self._url(), data=self._payload(), format="json")

        calls = mock_flows_cls.return_value.create_queue.call_args_list
        self.assertEqual(len(calls), 2)
        for call in calls:
            kwargs = call.kwargs if call.kwargs else call[1]
            self.assertEqual(kwargs.get("sector_uuid"), str(self.sector.uuid))
            self.assertEqual(kwargs.get("project_uuid"), str(self.project.uuid))
            self.assertIn("uuid", kwargs)
            self.assertIn("name", kwargs)

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @patch("chats.apps.api.v1.queues.viewsets.IntegratedTicketers")
    @with_project_permission()
    def test_uses_integrated_ticketers_when_its_principal_configured(
        self, mock_ticketers_cls, mock_feature_flag
    ):
        self.project.config = {"its_principal": True}
        self.project.save(update_fields=["config"])
        self.sector.secondary_project = {"uuid": str(uuid.uuid4())}
        self.sector.save(update_fields=["secondary_project"])

        mock_ticketers_cls.return_value.integrate_individual_topic.return_value = None

        response = self.client.post(self._url(), data=self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            mock_ticketers_cls.return_value.integrate_individual_topic.call_count, 2
        )

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @patch("chats.apps.api.v1.queues.viewsets.FlowRESTClient")
    @with_project_permission()
    def test_does_not_use_integrated_ticketers_when_not_configured(
        self, mock_flows_cls, mock_feature_flag
    ):
        mock_flows_cls.return_value.create_queue.return_value = make_flows_response(201)

        with patch(
            "chats.apps.api.v1.queues.viewsets.IntegratedTicketers"
        ) as mock_ticketers_cls:
            self.client.post(self._url(), data=self._payload(), format="json")
            mock_ticketers_cls.return_value.integrate_individual_topic.assert_not_called()

    @override_settings(USE_WENI_FLOWS=False)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @patch(
        "chats.apps.api.v1.queues.viewsets.QueueGroupSectorAuthorizationCreationUseCase"
    )
    @with_project_permission()
    def test_calls_group_sector_authorization_use_case_when_group_sector_exists(
        self, mock_use_case_cls, mock_feature_flag
    ):
        mock_use_case_cls.return_value.execute.return_value = None

        group_sector = GroupSector.objects.create(
            project=self.project,
            name="Grupo Test",
            rooms_limit=10,
        )
        SectorGroupSector.objects.create(
            sector_group=group_sector,
            sector=self.sector,
        )

        response = self.client.post(self._url(), data=self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(mock_use_case_cls.return_value.execute.call_count, 2)

    @override_settings(USE_WENI_FLOWS=False)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @patch(
        "chats.apps.api.v1.queues.viewsets.QueueGroupSectorAuthorizationCreationUseCase"
    )
    @with_project_permission()
    def test_does_not_call_group_sector_use_case_when_no_group_sector(
        self, mock_use_case_cls, mock_feature_flag
    ):
        mock_use_case_cls.return_value.execute.return_value = None

        response = self.client.post(self._url(), data=self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_use_case_cls.return_value.execute.assert_not_called()

    @override_settings(USE_WENI_FLOWS=False)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_creates_queue_authorizations_for_agents(self, mock_feature_flag):
        agent1 = User.objects.create(email="agent1@test.com")
        agent2 = User.objects.create(email="agent2@test.com")
        ProjectPermission.objects.create(user=agent1, project=self.project, role=2)
        ProjectPermission.objects.create(user=agent2, project=self.project, role=2)

        payload = self._payload(
            queues=[
                {"name": "Fila 1", "agents": ["agent1@test.com", "agent2@test.com"]},
                {"name": "Fila 2", "agents": ["agent1@test.com"]},
            ]
        )
        response = self.client.post(self._url(), data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        queue_1 = Queue.objects.get(sector=self.sector, name="Fila 1")
        queue_2 = Queue.objects.get(sector=self.sector, name="Fila 2")

        self.assertEqual(queue_1.authorizations.count(), 2)
        self.assertEqual(queue_2.authorizations.count(), 1)
        self.assertTrue(
            queue_1.authorizations.filter(permission__user=agent1).exists()
        )
        self.assertTrue(
            queue_1.authorizations.filter(permission__user=agent2).exists()
        )
        self.assertTrue(
            queue_2.authorizations.filter(permission__user=agent1).exists()
        )

    @override_settings(USE_WENI_FLOWS=False)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_creates_queues_without_agents_field(self, mock_feature_flag):
        response = self.client.post(self._url(), data=self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for queue in Queue.objects.filter(sector=self.sector):
            self.assertEqual(queue.authorizations.count(), 0)

    @override_settings(USE_WENI_FLOWS=False)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_agent_authorizations_have_agent_role(self, mock_feature_flag):
        agent = User.objects.create(email="agent@test.com")
        ProjectPermission.objects.create(user=agent, project=self.project, role=2)

        payload = self._payload(
            queues=[{"name": "Fila 1", "agents": ["agent@test.com"]}]
        )
        response = self.client.post(self._url(), data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        auth = QueueAuthorization.objects.get(
            queue__name="Fila 1", permission__user=agent
        )
        self.assertEqual(auth.role, QueueAuthorization.ROLE_AGENT)

    @override_settings(USE_WENI_FLOWS=False)
    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_ignores_agents_without_project_permission(self, mock_feature_flag):
        agent_with_perm = User.objects.create(email="valid@test.com")
        User.objects.create(email="noperm@test.com")
        ProjectPermission.objects.create(
            user=agent_with_perm, project=self.project, role=2
        )

        payload = self._payload(
            queues=[
                {"name": "Fila 1", "agents": ["valid@test.com", "noperm@test.com"]}
            ]
        )
        response = self.client.post(self._url(), data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        queue = Queue.objects.get(sector=self.sector, name="Fila 1")
        self.assertEqual(queue.authorizations.count(), 1)
        self.assertTrue(
            queue.authorizations.filter(permission__user=agent_with_perm).exists()
        )
