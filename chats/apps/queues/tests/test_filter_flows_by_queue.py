from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from chats.apps.api.utils import create_user_and_token
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.queues.usecases.filter_flows_by_queue import (
    filter_flows_by_user_queues,
)
from chats.apps.sectors.models import Sector

FLOW_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
FLOW_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
FLOW_C = "cccccccc-cccc-cccc-cccc-cccccccccccc"

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
