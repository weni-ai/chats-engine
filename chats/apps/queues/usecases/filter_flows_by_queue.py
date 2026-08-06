from typing import Any, Dict, List, Optional

from django.core.exceptions import ObjectDoesNotExist

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.queues.models import Queue


def prune_missing_selected_flows(
    queue: Queue,
    project,
    catalog_uuids: set,
    flows_client: Optional[FlowRESTClient] = None,
) -> List[str]:
    """
    Keep selected_flows that still exist in Flows.

    UUIDs present in the current catalog page are kept without an extra call.
    Missing ones are checked individually against Flows; deleted flows are
    removed from the queue bond.
    """
    selected = [str(flow_uuid) for flow_uuid in (queue.selected_flows or [])]
    if not selected:
        return []

    client = flows_client or FlowRESTClient()
    still_valid: List[str] = []

    for flow_uuid in selected:
        if flow_uuid in catalog_uuids:
            still_valid.append(flow_uuid)
            continue
        if client.flow_exists(project, flow_uuid):
            still_valid.append(flow_uuid)

    if still_valid != selected:
        queue.selected_flows = still_valid
        queue.save(update_fields=["selected_flows", "modified_on"])

    return still_valid


def filter_flows_by_user_queues(
    flow_list: Dict[str, Any],
    project,
    user,
    flows_client: Optional[FlowRESTClient] = None,
) -> Dict[str, Any]:
    """
    Filter the Flows catalog based on the user's queue configuration.

    Filtering only applies when the user belongs to exactly one queue and that
    queue has ``bond_flows_queue`` enabled. In every other case (no queues,
    multiple queues, or feature disabled) the original catalog is returned.

    When filtering is active, selected_flows that no longer exist in Flows are
    pruned from the queue before applying the filter.
    """
    try:
        permission = project.permissions.get(user=user, is_deleted=False)
    except ObjectDoesNotExist:
        return flow_list

    queue_ids = permission.queue_ids
    if not queue_ids:
        return flow_list

    queues = list(
        Queue.objects.filter(uuid__in=queue_ids, is_deleted=False).only(
            "uuid", "bond_flows_queue", "selected_flows"
        )
    )

    if len(queues) != 1:
        return flow_list

    queue = queues[0]
    if not queue.bond_flows_queue:
        return flow_list

    results = flow_list.get("results") or []
    catalog_uuids = {str(flow.get("uuid", "")) for flow in results}
    allowed = set(
        prune_missing_selected_flows(
            queue, project, catalog_uuids, flows_client=flows_client
        )
    )

    flow_list["results"] = [
        flow for flow in results if str(flow.get("uuid", "")) in allowed
    ]
    return flow_list
