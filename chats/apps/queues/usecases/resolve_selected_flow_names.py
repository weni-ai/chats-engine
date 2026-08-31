from typing import Dict, Iterable, List, Optional

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient


def collect_selected_flow_uuids(queues: Iterable) -> List[str]:
    uuids: List[str] = []
    for queue in queues:
        uuids.extend(str(flow_uuid) for flow_uuid in (queue.selected_flows or []))
    return uuids


def get_flow_name_map(
    project,
    flow_uuids: Iterable[str],
    flows_client: Optional[FlowRESTClient] = None,
) -> Dict[str, str]:
    unique_uuids = [
        str(flow_uuid) for flow_uuid in dict.fromkeys(flow_uuids) if flow_uuid
    ]
    if not unique_uuids or project is None:
        return {}

    client = flows_client or FlowRESTClient()
    names: Dict[str, str] = {}
    for flow_uuid in unique_uuids:
        flow = client.get_flow(project, flow_uuid)
        names[flow_uuid] = (flow or {}).get("name") or ""
    return names


def represent_selected_flows(instance, name_map: Optional[Dict[str, str]] = None):
    uuids = [str(flow_uuid) for flow_uuid in (instance.selected_flows or [])]
    mapping = name_map or {}
    return [
        {"uuid": flow_uuid, "name": mapping.get(flow_uuid, "")} for flow_uuid in uuids
    ]
