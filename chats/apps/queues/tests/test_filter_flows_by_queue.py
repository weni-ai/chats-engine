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


def catalog_copy():
    return dict(FULL_CATALOG, results=list(FULL_CATALOG["results"]))


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

    def test_no_associations_returns_all_flows(self):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=False,
            selected_flows=[],
        )
        self._authorize_queue(queue)

        result = filter_flows_by_user_queues(
            catalog_copy(), self.project, self.user
        )

        self.assertEqual(len(result["results"]), 3)

    def test_user_queues_plus_orphans(self):
        queue_1 = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A],
        )
        Queue.objects.create(
            name="Queue 2",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_C],
        )
        self._authorize_queue(queue_1)

        result = filter_flows_by_user_queues(
            catalog_copy(), self.project, self.user
        )

        self.assertEqual(
            [flow["uuid"] for flow in result["results"]],
            [FLOW_A, FLOW_B],
        )

    def test_user_in_multiple_queues_gets_union_plus_orphans(self):
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
            catalog_copy(), self.project, self.user
        )

        self.assertEqual(
            [flow["uuid"] for flow in result["results"]],
            [FLOW_A, FLOW_B, FLOW_C],
        )

    def test_queue_param_returns_only_that_queue_flows(self):
        queue_1 = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A],
        )
        Queue.objects.create(
            name="Queue 2",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_C],
        )
        self._authorize_queue(queue_1)

        result = filter_flows_by_user_queues(
            catalog_copy(),
            self.project,
            self.user,
            queue_uuid=str(queue_1.uuid),
        )

        self.assertEqual(
            [flow["uuid"] for flow in result["results"]],
            [FLOW_A],
        )

    def test_queue_param_unknown_queue_returns_empty(self):
        Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A],
        )

        result = filter_flows_by_user_queues(
            catalog_copy(),
            self.project,
            self.user,
            queue_uuid="11111111-1111-1111-1111-111111111111",
        )

        self.assertEqual(result["results"], [])

    def test_user_without_queues_returns_only_orphans(self):
        Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A],
        )

        result = filter_flows_by_user_queues(
            catalog_copy(), self.project, self.user
        )

        self.assertEqual(
            [flow["uuid"] for flow in result["results"]],
            [FLOW_B, FLOW_C],
        )

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
        Queue.objects.create(
            name="Queue 2",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_C],
        )
        self._authorize_queue(queue)

        flows_client = MagicMock()
        result = filter_flows_by_user_queues(
            catalog_copy(),
            self.project,
            self.user,
            flows_client=flows_client,
        )

        self.assertEqual(
            [flow["uuid"] for flow in result["results"]],
            [FLOW_A, FLOW_B],
        )
        flows_client.flow_exists.assert_not_called()

    def test_queue_param_prunes_deleted_flow(self):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A, FLOW_DELETED],
        )
        self._authorize_queue(queue)

        flows_client = MagicMock()
        flows_client.flow_exists.return_value = False

        result = filter_flows_by_user_queues(
            catalog_copy(),
            self.project,
            self.user,
            queue_uuid=str(queue.uuid),
            flows_client=flows_client,
        )

        self.assertEqual(
            [flow["uuid"] for flow in result["results"]],
            [FLOW_A],
        )
        flows_client.flow_exists.assert_called_once_with(self.project, FLOW_DELETED)
        queue.refresh_from_db()
        self.assertEqual(queue.selected_flows, [FLOW_A])


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
        return_value=catalog_copy(),
    )
    def test_list_flows_returns_user_queues_plus_orphans(self, mock_list):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_B],
        )
        Queue.objects.create(
            name="Queue 2",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_C],
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
            [FLOW_A, FLOW_B],
        )
        mock_list.assert_called_once()
        self.assertNotIn("queue", mock_list.call_args.kwargs)

    @patch(
        "chats.apps.api.v1.projects.viewsets.FlowRESTClient.list_flows",
        return_value=catalog_copy(),
    )
    def test_list_flows_filters_by_queue_query_param(self, mock_list):
        queue = Queue.objects.create(
            name="Queue 1",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_A],
        )
        Queue.objects.create(
            name="Queue 2",
            sector=self.sector,
            bond_flows_queue=True,
            selected_flows=[FLOW_C],
        )
        QueueAuthorization.objects.create(
            queue=queue,
            permission=self.permission,
            role=QueueAuthorization.ROLE_AGENT,
        )

        response = self.client.get(self.url, {"queue": str(queue.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [flow["uuid"] for flow in response.data["results"]],
            [FLOW_A],
        )
        mock_list.assert_called_once()
        _, kwargs = mock_list.call_args
        self.assertNotIn("queue", kwargs)

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
