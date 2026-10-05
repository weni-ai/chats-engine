from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase, override_settings

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.rooms.exceptions import (
    FlowsChangeTicketerError,
    FlowsTicketerNotFoundError,
)

CLIENT_PATH = "chats.apps.api.v1.internal.rest_clients.flows_rest_client"


def _build_response(status_code: int, payload=None, raise_on_json: bool = False):
    response = MagicMock()
    response.status_code = status_code
    response.content = b"" if payload is None else str(payload).encode()
    if raise_on_json:
        response.json.side_effect = ValueError("invalid json")
    else:
        response.json.return_value = payload or {}
    return response


def _build_project(token: str = "project-token"):
    project = MagicMock()
    project.flows_authorization = token
    return project


@override_settings(FLOWS_API_URL="https://flows.test")
class GetTicketerBySectorTests(TestCase):
    def setUp(self):
        self.project = _build_project()

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_returns_uuid_from_first_result(self, mock_retry):
        mock_retry.return_value = _build_response(
            200,
            {
                "results": [
                    {"uuid": "ticketer-uuid-1", "name": "T1"},
                    {"uuid": "ticketer-uuid-2", "name": "T2"},
                ]
            },
        )

        client = FlowRESTClient()

        result = client.get_ticketer_by_sector(self.project, "sector-uuid")

        self.assertEqual(result, "ticketer-uuid-1")
        call_kwargs = mock_retry.call_args.kwargs
        self.assertEqual(call_kwargs["project"], self.project)
        self.assertEqual(call_kwargs["request_method"], requests.get)
        self.assertEqual(
            call_kwargs["url"],
            "https://flows.test/api/v2/ticketers.json",
        )
        self.assertEqual(call_kwargs["params"], {"sector_uuid": "sector-uuid"})
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Token project-token")

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_raises_when_results_are_empty(self, mock_retry):
        mock_retry.return_value = _build_response(200, {"results": []})

        client = FlowRESTClient()

        with self.assertRaises(FlowsTicketerNotFoundError):
            client.get_ticketer_by_sector(self.project, "sector-uuid")

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_raises_on_non_200_status(self, mock_retry):
        mock_retry.return_value = _build_response(500, {"detail": "boom"})

        client = FlowRESTClient()

        with self.assertRaises(FlowsTicketerNotFoundError):
            client.get_ticketer_by_sector(self.project, "sector-uuid")

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_raises_on_invalid_json(self, mock_retry):
        mock_retry.return_value = _build_response(200, raise_on_json=True)

        client = FlowRESTClient()

        with self.assertRaises(FlowsTicketerNotFoundError):
            client.get_ticketer_by_sector(self.project, "sector-uuid")

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_raises_on_request_exception(self, mock_retry):
        mock_retry.side_effect = requests.ConnectionError("network down")

        client = FlowRESTClient()

        with self.assertRaises(FlowsTicketerNotFoundError):
            client.get_ticketer_by_sector(self.project, "sector-uuid")

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_raises_when_first_result_has_no_uuid(self, mock_retry):
        mock_retry.return_value = _build_response(200, {"results": [{"name": "T1"}]})

        client = FlowRESTClient()

        with self.assertRaises(FlowsTicketerNotFoundError):
            client.get_ticketer_by_sector(self.project, "sector-uuid")


@override_settings(FLOWS_API_URL="https://flows.test")
class ChangeTicketerTests(TestCase):
    def setUp(self):
        self.project = _build_project()

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_posts_change_ticketer_payload(self, mock_retry):
        mock_retry.return_value = _build_response(200, {})

        client = FlowRESTClient()

        client.change_ticketer(
            project=self.project,
            ticket_uuids=["ticket-1", "ticket-2"],
            ticketer_uuid="ticketer-1",
        )

        call_kwargs = mock_retry.call_args.kwargs
        self.assertEqual(call_kwargs["project"], self.project)
        self.assertEqual(call_kwargs["request_method"], requests.post)
        self.assertEqual(
            call_kwargs["url"],
            "https://flows.test/api/v2/ticket_actions.json",
        )
        self.assertEqual(
            call_kwargs["json"],
            {
                "tickets": ["ticket-1", "ticket-2"],
                "action": "change_ticketer",
                "ticketer": "ticketer-1",
            },
        )
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Token project-token")

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_raises_on_non_2xx_response(self, mock_retry):
        mock_retry.return_value = _build_response(400, {"detail": "bad"})

        client = FlowRESTClient()

        with self.assertRaises(FlowsChangeTicketerError) as ctx:
            client.change_ticketer(self.project, ["t-1"], "ticketer-1")

        self.assertEqual(ctx.exception.status_code, 400)

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_raises_on_request_exception(self, mock_retry):
        mock_retry.side_effect = requests.ConnectionError("boom")

        client = FlowRESTClient()

        with self.assertRaises(FlowsChangeTicketerError):
            client.change_ticketer(self.project, ["t-1"], "ticketer-1")


@override_settings(FLOWS_API_URL="https://flows.test")
class FlowExistsTests(TestCase):
    def setUp(self):
        self.project = _build_project()
        self.flow_uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_returns_true_when_flow_is_in_results(self, mock_retry):
        mock_retry.return_value = _build_response(
            200,
            {"results": [{"uuid": self.flow_uuid, "name": "Flow A"}]},
        )

        self.assertTrue(FlowRESTClient().flow_exists(self.project, self.flow_uuid))
        self.assertEqual(
            mock_retry.call_args.kwargs["url"],
            f"https://flows.test/api/v2/flows.json?uuid={self.flow_uuid}",
        )

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_returns_false_when_results_are_empty(self, mock_retry):
        mock_retry.return_value = _build_response(200, {"results": []})

        self.assertFalse(FlowRESTClient().flow_exists(self.project, self.flow_uuid))

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_returns_false_on_404(self, mock_retry):
        mock_retry.return_value = _build_response(404)

        self.assertFalse(FlowRESTClient().flow_exists(self.project, self.flow_uuid))

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_returns_true_on_unexpected_status_to_avoid_pruning(self, mock_retry):
        mock_retry.return_value = _build_response(500)

        self.assertTrue(FlowRESTClient().flow_exists(self.project, self.flow_uuid))


@override_settings(FLOWS_API_URL="https://flows.test")
class GetFlowTests(TestCase):
    def setUp(self):
        self.project = _build_project()
        self.flow_uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_returns_matching_flow(self, mock_retry):
        flow = {"uuid": self.flow_uuid, "name": "Flow A"}
        mock_retry.return_value = _build_response(200, {"results": [flow]})

        self.assertEqual(FlowRESTClient().get_flow(self.project, self.flow_uuid), flow)

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_returns_none_when_missing(self, mock_retry):
        mock_retry.return_value = _build_response(200, {"results": []})

        self.assertIsNone(FlowRESTClient().get_flow(self.project, self.flow_uuid))

    @patch(f"{CLIENT_PATH}.retry_request_and_refresh_flows_auth_token")
    def test_returns_none_on_error_status(self, mock_retry):
        mock_retry.return_value = _build_response(500)

        self.assertIsNone(FlowRESTClient().get_flow(self.project, self.flow_uuid))
