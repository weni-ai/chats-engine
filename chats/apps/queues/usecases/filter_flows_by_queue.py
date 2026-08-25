from typing import Any, Dict

from django.core.exceptions import ObjectDoesNotExist

from chats.apps.queues.models import Queue


def filter_flows_by_user_queues(
    flow_list: Dict[str, Any], project, user
) -> Dict[str, Any]:
    """
    Filter the Flows catalog based on the user's queue configuration.

    Filtering only applies when the user belongs to exactly one queue and that
    queue has ``bond_flows_queue`` enabled. In every other case (no queues,
    multiple queues, or feature disabled) the original catalog is returned.
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

    allowed = {str(flow_uuid) for flow_uuid in (queue.selected_flows or [])}
    results = flow_list.get("results") or []
    flow_list["results"] = [
        flow for flow in results if str(flow.get("uuid", "")) in allowed
    ]
    return flow_list
