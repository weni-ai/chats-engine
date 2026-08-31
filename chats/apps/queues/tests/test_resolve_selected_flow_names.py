from unittest.mock import MagicMock

from django.test import SimpleTestCase

from chats.apps.queues.usecases.resolve_selected_flow_names import (
    collect_selected_flow_uuids,
    get_flow_name_map,
    represent_selected_flows,
)


class ResolveSelectedFlowNamesTests(SimpleTestCase):
    def test_collect_selected_flow_uuids(self):
        queues = [
            MagicMock(selected_flows=["aaa", "bbb"]),
            MagicMock(selected_flows=["bbb"]),
            MagicMock(selected_flows=[]),
        ]

        self.assertEqual(
            collect_selected_flow_uuids(queues),
            ["aaa", "bbb", "bbb"],
        )

    def test_get_flow_name_map_returns_names(self):
        client = MagicMock()
        client.get_flow.side_effect = lambda _project, flow_uuid: {
            "aaa": {"uuid": "aaa", "name": "Flow A"},
            "bbb": {"uuid": "bbb", "name": "Flow B"},
        }.get(flow_uuid)

        names = get_flow_name_map(
            MagicMock(), ["aaa", "bbb", "aaa"], flows_client=client
        )

        self.assertEqual(names, {"aaa": "Flow A", "bbb": "Flow B"})
        self.assertEqual(client.get_flow.call_count, 2)

    def test_get_flow_name_map_uses_empty_name_when_missing(self):
        client = MagicMock()
        client.get_flow.return_value = None

        names = get_flow_name_map(MagicMock(), ["aaa"], flows_client=client)

        self.assertEqual(names, {"aaa": ""})

    def test_get_flow_name_map_skips_request_when_empty(self):
        client = MagicMock()

        self.assertEqual(get_flow_name_map(MagicMock(), [], flows_client=client), {})
        client.get_flow.assert_not_called()

    def test_represent_selected_flows(self):
        queue = MagicMock(selected_flows=["aaa", "bbb"])

        self.assertEqual(
            represent_selected_flows(queue, {"aaa": "Flow A"}),
            [
                {"uuid": "aaa", "name": "Flow A"},
                {"uuid": "bbb", "name": ""},
            ],
        )
