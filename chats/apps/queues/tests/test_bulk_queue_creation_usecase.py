import uuid
from datetime import time
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework import exceptions, status

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.queues.usecases.bulk_queue_creation import BulkQueueCreationUseCase
from chats.apps.sectors.models import GroupSector, Sector, SectorGroupSector


def make_flows_response(status_code=status.HTTP_201_CREATED):
    response = MagicMock()
    response.status_code = status_code
    response.content = b""
    return response


class BulkQueueCreationUseCaseTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Test Sector",
            rooms_limit=5,
            work_start=time(hour=9, minute=0),
            work_end=time(hour=18, minute=0),
        )

    def _queues_data(self, queues=None):
        return queues or [{"name": "Fila 1"}, {"name": "Fila 2"}]

    @override_settings(USE_WENI_FLOWS=False)
    def test_persists_all_queues_in_db(self):
        use_case = BulkQueueCreationUseCase(
            sector=self.sector, queues_data=self._queues_data()
        )

        created = use_case.execute()

        self.assertEqual(len(created), 2)
        self.assertEqual(Queue.objects.filter(sector=self.sector).count(), 2)

    @override_settings(USE_WENI_FLOWS=False)
    def test_persists_optional_fields_correctly(self):
        use_case = BulkQueueCreationUseCase(
            sector=self.sector,
            queues_data=[
                {
                    "name": "Fila Completa",
                    "default_message": "Olá",
                    "config": {"foo": "bar"},
                    "queue_limit": {"limit": 7, "is_active": True},
                }
            ],
        )

        use_case.execute()

        queue = Queue.objects.get(sector=self.sector, name="Fila Completa")
        self.assertEqual(queue.default_message, "Olá")
        self.assertEqual(queue.config, {"foo": "bar"})
        self.assertEqual(queue.queue_limit, 7)
        self.assertTrue(queue.is_queue_limit_active)

    @override_settings(USE_WENI_FLOWS=False)
    def test_creates_queue_authorizations_for_agents_with_project_permission(self):
        agent = User.objects.create(email="agent@test.com")
        ProjectPermission.objects.create(
            user=agent, project=self.project, role=ProjectPermission.ROLE_ATTENDANT
        )

        use_case = BulkQueueCreationUseCase(
            sector=self.sector,
            queues_data=[{"name": "Fila 1", "agents": ["agent@test.com"]}],
        )
        use_case.execute()

        queue = Queue.objects.get(sector=self.sector, name="Fila 1")
        self.assertEqual(queue.authorizations.count(), 1)
        auth = queue.authorizations.first()
        self.assertEqual(auth.permission.user, agent)
        self.assertEqual(auth.role, QueueAuthorization.ROLE_AGENT)

    @override_settings(USE_WENI_FLOWS=False)
    def test_ignores_agents_without_project_permission(self):
        agent_with = User.objects.create(email="with@test.com")
        User.objects.create(email="without@test.com")
        ProjectPermission.objects.create(
            user=agent_with,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        use_case = BulkQueueCreationUseCase(
            sector=self.sector,
            queues_data=[
                {
                    "name": "Fila 1",
                    "agents": ["with@test.com", "without@test.com"],
                }
            ],
        )
        use_case.execute()

        queue = Queue.objects.get(sector=self.sector, name="Fila 1")
        self.assertEqual(queue.authorizations.count(), 1)
        self.assertTrue(
            queue.authorizations.filter(permission__user=agent_with).exists()
        )

    @override_settings(USE_WENI_FLOWS=False)
    @patch(
        "chats.apps.queues.usecases.bulk_queue_creation."
        "QueueGroupSectorAuthorizationCreationUseCase"
    )
    def test_runs_group_sector_use_case_when_sector_belongs_to_group(
        self, mock_group_sector_uc
    ):
        group = GroupSector.objects.create(
            project=self.project, name="Group", rooms_limit=10
        )
        SectorGroupSector.objects.create(sector_group=group, sector=self.sector)

        use_case = BulkQueueCreationUseCase(
            sector=self.sector, queues_data=self._queues_data()
        )
        use_case.execute()

        self.assertEqual(mock_group_sector_uc.return_value.execute.call_count, 2)

    @override_settings(USE_WENI_FLOWS=False)
    @patch(
        "chats.apps.queues.usecases.bulk_queue_creation."
        "QueueGroupSectorAuthorizationCreationUseCase"
    )
    def test_does_not_run_group_sector_use_case_when_sector_is_standalone(
        self, mock_group_sector_uc
    ):
        use_case = BulkQueueCreationUseCase(
            sector=self.sector, queues_data=self._queues_data()
        )
        use_case.execute()

        mock_group_sector_uc.return_value.execute.assert_not_called()

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.queues.usecases.bulk_queue_creation.FlowRESTClient")
    def test_calls_flows_create_queue_for_each_persisted_queue(self, mock_flows):
        mock_flows.return_value.create_queue.return_value = make_flows_response()

        use_case = BulkQueueCreationUseCase(
            sector=self.sector, queues_data=self._queues_data()
        )
        use_case.execute()

        self.assertEqual(mock_flows.return_value.create_queue.call_count, 2)
        for call in mock_flows.return_value.create_queue.call_args_list:
            self.assertEqual(call.kwargs["sector_uuid"], str(self.sector.uuid))
            self.assertEqual(call.kwargs["project_uuid"], str(self.project.uuid))

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.queues.usecases.bulk_queue_creation.FlowRESTClient")
    def test_rolls_back_db_and_skips_destroy_when_first_flows_call_fails(
        self, mock_flows
    ):
        mock_flows.return_value.create_queue.return_value = make_flows_response(500)

        use_case = BulkQueueCreationUseCase(
            sector=self.sector, queues_data=self._queues_data()
        )

        with self.assertRaises(exceptions.APIException):
            use_case.execute()

        self.assertEqual(Queue.objects.filter(sector=self.sector).count(), 0)
        mock_flows.return_value.destroy_queue.assert_not_called()

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.queues.usecases.bulk_queue_creation.FlowRESTClient")
    def test_compensates_already_synced_queues_when_later_flows_call_fails(
        self, mock_flows
    ):
        mock_flows.return_value.create_queue.side_effect = [
            make_flows_response(),
            make_flows_response(500),
        ]
        mock_flows.return_value.destroy_queue.return_value = make_flows_response(200)

        use_case = BulkQueueCreationUseCase(
            sector=self.sector, queues_data=self._queues_data()
        )

        with self.assertRaises(exceptions.APIException):
            use_case.execute()

        self.assertEqual(Queue.objects.filter(sector=self.sector).count(), 0)
        self.assertEqual(mock_flows.return_value.destroy_queue.call_count, 1)

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.queues.usecases.bulk_queue_creation.FlowRESTClient")
    def test_does_not_break_when_flows_destroy_fails_during_rollback(self, mock_flows):
        mock_flows.return_value.create_queue.side_effect = [
            make_flows_response(),
            make_flows_response(500),
        ]
        mock_flows.return_value.destroy_queue.side_effect = Exception("network error")

        use_case = BulkQueueCreationUseCase(
            sector=self.sector, queues_data=self._queues_data()
        )

        with self.assertRaises(exceptions.APIException):
            use_case.execute()

        self.assertEqual(Queue.objects.filter(sector=self.sector).count(), 0)

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.queues.usecases.bulk_queue_creation.IntegratedTicketers")
    def test_calls_integrated_ticketers_once_when_project_is_principal(
        self, mock_ticketers
    ):
        self.project.config = {"its_principal": True}
        self.project.save(update_fields=["config"])
        self.sector.secondary_project = {"uuid": str(uuid.uuid4())}
        self.sector.save(update_fields=["secondary_project"])

        use_case = BulkQueueCreationUseCase(
            sector=self.sector, queues_data=self._queues_data()
        )
        use_case.execute()

        mock_ticketers.return_value.integrate_individual_topic.assert_called_once_with(
            self.project, self.sector.secondary_project
        )

    @override_settings(USE_WENI_FLOWS=False)
    def test_db_unique_constraint_conflict_raises_validation_error(self):
        Queue.all_objects.create(
            name="Fila Conflito", sector=self.sector, is_deleted=True
        )

        use_case = BulkQueueCreationUseCase(
            sector=self.sector,
            queues_data=[{"name": "Fila Conflito"}],
        )

        with self.assertRaises(exceptions.ValidationError):
            use_case.execute()

        self.assertEqual(Queue.objects.filter(sector=self.sector).count(), 0)

    @override_settings(USE_WENI_FLOWS=True)
    @patch("chats.apps.queues.usecases.bulk_queue_creation.FlowRESTClient")
    def test_does_not_call_integrated_ticketers_when_project_is_not_principal(
        self, mock_flows
    ):
        mock_flows.return_value.create_queue.return_value = make_flows_response()

        with patch(
            "chats.apps.queues.usecases.bulk_queue_creation.IntegratedTicketers"
        ) as mock_ticketers:
            use_case = BulkQueueCreationUseCase(
                sector=self.sector, queues_data=self._queues_data()
            )
            use_case.execute()

            mock_ticketers.return_value.integrate_individual_topic.assert_not_called()
