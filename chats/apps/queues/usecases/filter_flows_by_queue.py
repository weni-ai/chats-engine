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


def _project_queues(project) -> List[Queue]:
    return list(
        Queue.objects.filter(sector__project=project, is_deleted=False).only(
            "uuid", "bond_flows_queue", "selected_flows"
        )
    )


def _apply_allowed_uuids(flow_list: Dict[str, Any], allowed: set) -> Dict[str, Any]:
    results = flow_list.get("results") or []
    flow_list["results"] = [
        flow for flow in results if str(flow.get("uuid", "")) in allowed
    ]
    return flow_list


def filter_flows_by_user_queues(
    flow_list: Dict[str, Any],
    project,
    user,
    queue_uuid: Optional[str] = None,
    flows_client: Optional[FlowRESTClient] = None,
) -> Dict[str, Any]:
    """
    Filter the Flows catalog based on queue associations.

    ``queue_uuid`` is applied only in this engine; it is never forwarded to
    Flows. When it is set, only flows bonded to that queue are returned.

    When it is omitted:
    - if no queue in the project has selected flows, the original catalog
      is returned;
    - otherwise the result is the union of flows bonded to the user's queues
      plus catalog flows that are not bonded to any queue.

    When filtering is active, selected_flows that no longer exist in Flows are
    pruned from the relevant queues before applying the filter.
    """
    results = flow_list.get("results") or []
    catalog_uuids = {str(flow.get("uuid", "")) for flow in results}
    project_queues = _project_queues(project)

    if queue_uuid:
        queue = next(
            (item for item in project_queues if str(item.uuid) == str(queue_uuid)),
            None,
        )
        if queue is None:
            flow_list["results"] = []
            return flow_list
        allowed = set(
            prune_missing_selected_flows(
                queue, project, catalog_uuids, flows_client=flows_client
            )
        )
        return _apply_allowed_uuids(flow_list, allowed)

    if not any(queue.selected_flows for queue in project_queues):
        return flow_list

    try:
        permission = project.permissions.get(user=user, is_deleted=False)
        user_queue_ids = {str(queue_id) for queue_id in (permission.queue_ids or [])}
    except ObjectDoesNotExist:
        user_queue_ids = set()

    associated_anywhere: set = set()
    user_associated: set = set()

    for queue in project_queues:
        queue_id = str(queue.uuid)
        if queue_id in user_queue_ids and queue.selected_flows:
            selected = prune_missing_selected_flows(
                queue, project, catalog_uuids, flows_client=flows_client
            )
        else:
            selected = [str(flow_uuid) for flow_uuid in (queue.selected_flows or [])]

        associated_anywhere.update(selected)
        if queue_id in user_queue_ids:
            user_associated.update(selected)

    orphans = catalog_uuids - associated_anywhere
    return _apply_allowed_uuids(flow_list, user_associated | orphans)
