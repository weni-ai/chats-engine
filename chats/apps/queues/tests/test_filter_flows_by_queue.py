from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.queues.usecases.filter_flows_by_queue import (
    filter_flows_by_user_queues,
    prune_missing_selected_flows,
)
from chats.apps.sectors.models import Sector

FLOW_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
FLOW_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
FLOW_C = "cccccccc-cccc-cccc-cccc-cccccccccccc"
FLOW_DELETED = "dddddddd-dddd-dddd-dddd-dddddddddddd"

FULL_CATALOG = {
    "next": None,
    "previous": None,
    "results": [
        {"uuid": FLOW_A, "name": "Flow A"},
        {"uuid": FLOW_B, "name": "Flow B"},
        {"uuid": FLOW_C, "name": "Flow C"},
    ],
}


class FilterFlowsByUserQueuesTestCase(TestCase):
    def setUp(self):
        self.user, _ = create_user_and_token("filterflows")
        self.project = Project.objects.create(name="Filter Flows Project")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )

    def _authorize_queue(self, queue: Queue) -> QueueAuthorization:
        return QueueAuthorization.objects.create(
            queue=queue,
            permission=self.permission,
            role=QueueAuthorization.ROLE_AGENT,
        )

    def test_single_queue_with_feature_off_returns_all_flows(self):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=False,
            selected_flows=[],
        )
        self._authorize_queue(queue)

        result = filter_flows_by_user_queues(
            dict(FULL_CATALOG, results=list(FULL_CATALOG["results"])),
            self.project,
            self.user,
        )

        self.assertEqual(len(result["results"]), 3)

    def test_single_queue_with_feature_on_filters_selected_flows(self):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A, FLOW_C],
        )
        self._authorize_queue(queue)

        result = filter_flows_by_user_queues(
            dict(FULL_CATALOG, results=list(FULL_CATALOG["results"])),
            self.project,
            self.user,
        )

        self.assertEqual(
            [flow["uuid"] for flow in result["results"]],
            [FLOW_A, FLOW_C],
        )

    def test_multiple_queues_returns_all_flows(self):
        queue_1 = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A],
        )
        queue_2 = Queue.objects.create(
            name="Queue 2",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_B],
        )
        self._authorize_queue(queue_1)
        self._authorize_queue(queue_2)

        result = filter_flows_by_user_queues(
            dict(FULL_CATALOG, results=list(FULL_CATALOG["results"])),
            self.project,
            self.user,
        )

        self.assertEqual(len(result["results"]), 3)

    def test_multiple_queues_with_one_without_filter_returns_all_flows(self):
        queue_1 = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A],
        )
        queue_2 = Queue.objects.create(
            name="Queue 2",
            sector=self.sector,
            bond_flows_queue=False,
            selected_flows=[],
        )
        self._authorize_queue(queue_1)
        self._authorize_queue(queue_2)

        result = filter_flows_by_user_queues(
            dict(FULL_CATALOG, results=list(FULL_CATALOG["results"])),
            self.project,
            self.user,
        )

        self.assertEqual(len(result["results"]), 3)

    def test_single_queue_with_feature_on_and_empty_selected_flows_returns_empty(self):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[],
        )
        self._authorize_queue(queue)

        result = filter_flows_by_user_queues(
            dict(FULL_CATALOG, results=list(FULL_CATALOG["results"])),
            self.project,
            self.user,
        )

        self.assertEqual(result["results"], [])

    def test_user_without_queues_returns_all_flows(self):
        Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A],
        )

        result = filter_flows_by_user_queues(
            dict(FULL_CATALOG, results=list(FULL_CATALOG["results"])),
            self.project,
            self.user,
        )

        self.assertEqual(len(result["results"]), 3)

    def test_prunes_deleted_flow_not_in_current_page(self):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A, FLOW_DELETED],
        )
        self._authorize_queue(queue)

        flows_client = MagicMock()
        flows_client.flow_exists.return_value = False

        page = {
            "next": "cursor-next",
            "previous": None,
            "results": [{"uuid": FLOW_A, "name": "Flow A"}],
        }
        result = filter_flows_by_user_queues(
            page, self.project, self.user, flows_client=flows_client
        )

        self.assertEqual([flow["uuid"] for flow in result["results"]], [FLOW_A])
        flows_client.flow_exists.assert_called_once_with(self.project, FLOW_DELETED)

        queue.refresh_from_db()
        self.assertEqual(queue.selected_flows, [FLOW_A])

    def test_keeps_flow_missing_from_page_when_it_still_exists_in_flows(self):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A, FLOW_B],
        )
        self._authorize_queue(queue)

        flows_client = MagicMock()
        flows_client.flow_exists.return_value = True

        page = {
            "next": "cursor-next",
            "previous": None,
            "results": [{"uuid": FLOW_A, "name": "Flow A"}],
        }
        result = filter_flows_by_user_queues(
            page, self.project, self.user, flows_client=flows_client
        )

        self.assertEqual([flow["uuid"] for flow in result["results"]], [FLOW_A])
        flows_client.flow_exists.assert_called_once_with(self.project, FLOW_B)

        queue.refresh_from_db()
        self.assertEqual(queue.selected_flows, [FLOW_A, FLOW_B])

    def test_does_not_call_flows_for_uuids_present_in_catalog_page(self):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A, FLOW_B],
        )
        self._authorize_queue(queue)

        flows_client = MagicMock()
        result = filter_flows_by_user_queues(
            dict(FULL_CATALOG, results=list(FULL_CATALOG["results"])),
            self.project,
            self.user,
            flows_client=flows_client,
        )

        self.assertEqual(
            [flow["uuid"] for flow in result["results"]],
            [FLOW_A, FLOW_B],
        )
        flows_client.flow_exists.assert_not_called()


class PruneMissingSelectedFlowsTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Prune Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A, FLOW_DELETED],
        )

    def test_prune_removes_only_missing_flows(self):
        flows_client = MagicMock()
        flows_client.flow_exists.return_value = False

        still_valid = prune_missing_selected_flows(
            self.queue,
            self.project,
            catalog_uuids={FLOW_A},
            flows_client=flows_client,
        )

        self.assertEqual(still_valid, [FLOW_A])
        self.queue.refresh_from_db()
        self.assertEqual(self.queue.selected_flows, [FLOW_A])


class ListFlowsFilterIntegrationTestCase(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("listflows")
        self.project = Project.objects.create(
            name="List Flows Project", flows_authorization="fake-token"
        )
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.url = reverse("project-flows", kwargs={"uuid": str(self.project.uuid)})
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch(
        "chats.apps.api.v1.projects.viewsets.FlowRESTClient.list_flows",
        return_value=dict(FULL_CATALOG, results=list(FULL_CATALOG["results"])),
    )
    def test_list_flows_filters_when_user_has_single_bonded_queue(self, mock_list):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_B],
        )
        QueueAuthorization.objects.create(
            queue=queue,
            permission=self.permission,
            role=QueueAuthorization.ROLE_AGENT,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [flow["uuid"] for flow in response.data["results"]],
            [FLOW_B],
        )
        mock_list.assert_called_once()

    @patch(
        "chats.apps.api.v1.projects.viewsets.FlowRESTClient.list_flows",
        return_value=dict(FULL_CATALOG, results=list(FULL_CATALOG["results"])),
    )
    def test_list_flows_returns_all_when_user_has_multiple_queues(self, mock_list):
        queue_1 = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A],
        )
        queue_2 = Queue.objects.create(
            name="Queue 2",
            sector=self.sector,
            bond_flows_queue=False,
        )
        for queue in (queue_1, queue_2):
            QueueAuthorization.objects.create(
                queue=queue,
                permission=self.permission,
                role=QueueAuthorization.ROLE_AGENT,
            )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)

    @patch(
        "chats.apps.queues.usecases.filter_flows_by_queue.FlowRESTClient.flow_exists",
        return_value=False,
    )
    @patch(
        "chats.apps.api.v1.projects.viewsets.FlowRESTClient.list_flows",
        return_value={
            "next": None,
            "previous": None,
            "results": [{"uuid": FLOW_A, "name": "Flow A"}],
        },
    )
    def test_list_flows_prunes_deleted_selected_flow(
        self, mock_list, mock_flow_exists
    ):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A, FLOW_DELETED],
        )
        QueueAuthorization.objects.create(
            queue=queue,
            permission=self.permission,
            role=QueueAuthorization.ROLE_AGENT,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [flow["uuid"] for flow in response.data["results"]],
            [FLOW_A],
        )
        mock_flow_exists.assert_called_once_with(self.project, FLOW_DELETED)

        queue.refresh_from_db()
        self.assertEqual(queue.selected_flows, [FLOW_A])
