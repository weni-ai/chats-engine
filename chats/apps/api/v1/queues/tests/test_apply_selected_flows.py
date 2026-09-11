from types import SimpleNamespace
from uuid import uuid4

from django.test import SimpleTestCase

from chats.apps.api.v1.queues.serializers import apply_selected_flows


class ApplySelectedFlowsTests(SimpleTestCase):
    def test_clears_selected_flows_when_bond_is_disabled_on_create(self):
        serializer = SimpleNamespace(
            initial_data={"bond_flows_queue": False}, instance=None
        )
        data = {"bond_flows_queue": False, "selected_flows": [uuid4()]}

        result = apply_selected_flows(serializer, data)

        self.assertEqual(result["selected_flows"], [])

    def test_keeps_existing_selected_flows_when_bond_not_in_payload(self):
        instance = SimpleNamespace(bond_flows_queue=True)
        serializer = SimpleNamespace(initial_data={"name": "Queue"}, instance=instance)
        existing = [str(uuid4())]
        data = {"selected_flows": existing}

        result = apply_selected_flows(serializer, data)

        self.assertEqual(result["selected_flows"], existing)

    def test_coerces_uuids_to_str_when_bond_is_enabled(self):
        flow_uuid = uuid4()
        serializer = SimpleNamespace(
            initial_data={"bond_flows_queue": True, "selected_flows": [flow_uuid]},
            instance=None,
        )
        data = {"bond_flows_queue": True, "selected_flows": [flow_uuid]}

        result = apply_selected_flows(serializer, data)

        self.assertEqual(result["selected_flows"], [str(flow_uuid)])

    def test_defaults_selected_flows_on_create_when_missing(self):
        serializer = SimpleNamespace(
            initial_data={"bond_flows_queue": True},
            instance=None,
        )
        data = {"bond_flows_queue": True}

        result = apply_selected_flows(serializer, data)

        self.assertEqual(result["selected_flows"], [])
