import json

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.dashboard.tasks import close_metrics, generate_metrics
from chats.apps.rooms.models import Room


def close_room(room_pk: str):
    if settings.USE_CELERY:
        transaction.on_commit(
            lambda: close_metrics.apply_async(
                args=[room_pk], queue=settings.METRICS_CUSTOM_QUEUE
            )
        )
    generate_metrics(room_pk)


def update_custom_fields(room: Room, custom_fields_update: dict):
    room.custom_fields.update(custom_fields_update)
    room.save()


def update_flows_custom_fields(project, data, contact_id):
    response = FlowRESTClient().create_contact(
        project=project,
        data=data,
        contact_id=contact_id,
    )
    if response.status_code not in [status.HTTP_200_OK]:
        raise APIException(
            {
                "Detail": f"[{response.status_code}]\n"
                + f"Error updating custom fields on flows. Exception: {response.content}"
            },
        )


def get_editable_custom_fields_room(room_filter: dict) -> Room:
    try:
        room = Room.objects.get(**room_filter)
    except Room.DoesNotExist:
        raise APIException(detail="Active room not found.")

    if not room.queue.sector.can_edit_custom_fields:
        raise APIException(
            detail="Access denied! You can't edit custom fields in this sector."
        )

    return room


def create_transfer_json(action: str, from_, to):
    if hasattr(from_, "meta"):
        return {
            "action": action,
            "from": {"type": from_._meta.model_name, "name": from_.name},
            "to": {"type": to._meta.model_name, "name": to.name},
        }
    else:
        return {
            "action": action,
            "from": {"type": "", "name": ""},
            "to": {"type": to._meta.model_name, "name": to.name},
        }


def create_feedback_json(method: str, content: dict):
    return {"method": method, "content": content}


def create_room_feedback_message(room: object, feedback: dict, method: str):
    msg = room.messages.create(
        text=json.dumps(create_feedback_json(method=method, content=feedback)),
        seen=True,
    )
    msg.notify_room("create")
