from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase, override_settings

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import (
    FlowRESTClient,
)
from chats.apps.rooms.exceptions import (
    FlowsChangeTicketerError,
    FlowsTicketerNotFoundError,
)


def _build_response(status_code: int, payload=None, raise_on_json: bool = False):
    response = MagicMock()
    response.status_code = status_code
    response.content = b"" if payload is None else str(payload).encode()
    if raise_on_json:
        response.json.side_effect = ValueError("invalid json")
    else:
        response.json.return_value = payload or {}
    return response


@override_settings(FLOWS_API_URL="https://flows.test")
class GetTicketerBySectorTests(TestCase):
    def setUp(self):
        patcher = patch.object(
            FlowRESTClient, "headers", new={"Authorization": "Bearer test"}
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.flows_rest_client.requests.get"
    )
    def test_returns_uuid_from_first_result(self, mock_get):
        mock_get.return_value = _build_response(
            200,
            {
                "results": [
                    {"uuid": "ticketer-uuid-1", "name": "T1"},
                    {"uuid": "ticketer-uuid-2", "name": "T2"},
                ]
            },
        )

        client = FlowRESTClient()

        result = client.get_ticketer_by_sector("sector-uuid")

        self.assertEqual(result, "ticketer-uuid-1")
        called_url, _ = mock_get.call_args[0], mock_get.call_args[1]
        # Validate that request was made to /api/v2/ticketers.json with sector_uuid param
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://flows.test/api/v2/ticketers.json",
        )
        self.assertEqual(
            mock_get.call_args.kwargs["params"],
            {"sector_uuid": "sector-uuid"},
        )
        self.assertIn("Authorization", mock_get.call_args.kwargs["headers"])
        self.assertEqual(
            mock_get.call_args.kwargs["headers"]["Accept"],
            "application/json",
        )

    @patch(
        "chats.apps.api.v1.internal.rest_clients.flows_rest_client.requests.get"
    )
    def test_raises_when_results_are_empty(self, mock_get):
        mock_get.return_value = _build_response(200, {"results": []})

        client = FlowRESTClient()

        with self.assertRaises(FlowsTicketerNotFoundError):
            client.get_ticketer_by_sector("sector-uuid")

    @patch(
        "chats.apps.api.v1.internal.rest_clients.flows_rest_client.requests.get"
    )
    def test_raises_on_non_200_status(self, mock_get):
        mock_get.return_value = _build_response(500, {"detail": "boom"})

        client = FlowRESTClient()

        with self.assertRaises(FlowsTicketerNotFoundError):
            client.get_ticketer_by_sector("sector-uuid")

    @patch(
        "chats.apps.api.v1.internal.rest_clients.flows_rest_client.requests.get"
    )
    def test_raises_on_invalid_json(self, mock_get):
        mock_get.return_value = _build_response(200, raise_on_json=True)

        client = FlowRESTClient()

        with self.assertRaises(FlowsTicketerNotFoundError):
            client.get_ticketer_by_sector("sector-uuid")

    @patch(
        "chats.apps.api.v1.internal.rest_clients.flows_rest_client.requests.get"
    )
    def test_raises_on_request_exception(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("network down")

        client = FlowRESTClient()

        with self.assertRaises(FlowsTicketerNotFoundError):
            client.get_ticketer_by_sector("sector-uuid")

    @patch(
        "chats.apps.api.v1.internal.rest_clients.flows_rest_client.requests.get"
    )
    def test_raises_when_first_result_has_no_uuid(self, mock_get):
        mock_get.return_value = _build_response(
            200, {"results": [{"name": "T1"}]}
        )

        client = FlowRESTClient()

        with self.assertRaises(FlowsTicketerNotFoundError):
            client.get_ticketer_by_sector("sector-uuid")


@override_settings(FLOWS_API_URL="https://flows.test")
class ChangeTicketerTests(TestCase):
    def setUp(self):
        patcher = patch.object(
            FlowRESTClient, "headers", new={"Authorization": "Bearer test"}
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.flows_rest_client."
        "get_request_session_with_retries"
    )
    def test_posts_change_ticketer_payload(self, mock_session_factory):
        session = MagicMock()
        session.post.return_value = _build_response(200, {})
        mock_session_factory.return_value = session

        client = FlowRESTClient()

        client.change_ticketer(
            ticket_uuids=["ticket-1", "ticket-2"],
            ticketer_uuid="ticketer-1",
        )

        url = session.post.call_args.args[0]
        self.assertEqual(url, "https://flows.test/api/v2/ticket_actions.json")
        body_kwarg = session.post.call_args.kwargs["data"]
        self.assertIn('"action": "change_ticketer"', body_kwarg)
        self.assertIn('"ticketer": "ticketer-1"', body_kwarg)
        self.assertIn('"ticket-1"', body_kwarg)
        self.assertIn('"ticket-2"', body_kwarg)
        headers = session.post.call_args.kwargs["headers"]
        self.assertEqual(headers["Accept"], "application/json")
        self.assertIn("Authorization", headers)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.flows_rest_client."
        "get_request_session_with_retries"
    )
    def test_raises_on_non_2xx_response(self, mock_session_factory):
        session = MagicMock()
        session.post.return_value = _build_response(400, {"detail": "bad"})
        mock_session_factory.return_value = session

        client = FlowRESTClient()

        with self.assertRaises(FlowsChangeTicketerError) as ctx:
            client.change_ticketer(["t-1"], "ticketer-1")

        self.assertEqual(ctx.exception.status_code, 400)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.flows_rest_client."
        "get_request_session_with_retries"
    )
    def test_raises_on_request_exception(self, mock_session_factory):
        session = MagicMock()
        session.post.side_effect = requests.ConnectionError("boom")
        mock_session_factory.return_value = session

        client = FlowRESTClient()

        with self.assertRaises(FlowsChangeTicketerError):
            client.change_ticketer(["t-1"], "ticketer-1")
