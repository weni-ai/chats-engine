import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.contacts.usecases.out_off_whatsapp_response_window import (
    out_off_whatsapp_response_window,
)
from chats.apps.projects.models import ContactGroupFlowReference
from chats.apps.projects.usecases.exceptions import (
    ActiveFlowStartError,
    NoContactsToStartFlowError,
    StartFlowPermissionError,
)
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.models import Room
from chats.apps.rooms.views import create_room_feedback_message

logger = logging.getLogger(__name__)


class StartFlowUseCase:
    def execute(self, project, user, data):
        try:
            perm = project.permissions.get(user=user)
        except ObjectDoesNotExist:
            raise StartFlowPermissionError(
                "the user does not have permission in this project"
            )

        contact_id = data.get("contacts")[0]
        flow_start_data = {
            "permission": perm,
            "flow": data.get("flow", None),
            "contact_data": {
                "name": data.pop("contact_name"),
                "external_id": contact_id,
            },
        }
        room_id = data.get("room", None)

        with transaction.atomic():
            try:
                room = Room.objects.get(
                    pk=room_id, is_active=True, contact__external_id=contact_id
                )
                if room.flowstarts.filter(is_deleted=False).exists():
                    raise ActiveFlowStartError(
                        "There already is an active flow start for this room"
                    )

                if not room.is_24h_valid:
                    flow_start_data["room"] = room
                    room.request_callback(room.serialized_ws_data)
                    room.is_waiting = True
                    room.save()
            except ObjectDoesNotExist:
                pass
            except ValidationError as exc:
                logger.warning("ValidationError ao buscar room %s: %s", room_id, exc)

            chats_flow_start = project.flowstarts.create(**flow_start_data)
            self._create_flow_start_instances(data, chats_flow_start)

            _status_code, flow_start = FlowRESTClient().start_flow(project, data)
            chats_flow_start.external_id = flow_start.get("uuid")
            chats_flow_start.name = flow_start.get("flow").get("name")
            chats_flow_start.save()
            if chats_flow_start.room:
                create_room_feedback_message(
                    chats_flow_start.room,
                    {"name": chats_flow_start.name},
                    method=RoomFeedbackMethods.FLOW_START,
                    requested_by=user,
                )
                chats_flow_start.room.notify_room("update")
        return flow_start

    def execute_for_contacts(self, project, user, flow, contact_external_ids):
        try:
            perm = project.permissions.get(user=user)
        except ObjectDoesNotExist:
            raise StartFlowPermissionError(
                "the user does not have permission in this project"
            )

        external_ids = list(dict.fromkeys(contact_external_ids))
        if not external_ids:
            raise NoContactsToStartFlowError("No contacts to start the flow.")

        with transaction.atomic():
            chats_flow_start = project.flowstarts.create(
                permission=perm,
                flow=flow,
                contact_data={"external_ids": external_ids},
            )
            self._create_flow_start_instances(
                {"contacts": external_ids}, chats_flow_start
            )
            _status_code, flow_start = FlowRESTClient().start_flow(
                project, {"flow": flow, "contacts": external_ids}
            )
            chats_flow_start.external_id = flow_start.get("uuid")
            chats_flow_start.name = flow_start.get("flow").get("name")
            chats_flow_start.save()
        return flow_start

    def _create_flow_start_instances(self, data, flow_start):
        groups = data.get("groups", [])
        contacts = data.get("contacts", [])
        instances = []
        for group in groups:
            instances.append(
                ContactGroupFlowReference(
                    receiver_type="group", external_id=group, flow_start=flow_start
                )
            )

        for contact in contacts:
            instances.append(
                ContactGroupFlowReference(
                    receiver_type="contact", external_id=contact, flow_start=flow_start
                )
            )

        flow_start.references.bulk_create(instances)


class StartOutOffWhatsappFlowUseCase:
    def execute(self, project, user, flow, ignored_contacts, filters):
        contacts, _ = out_off_whatsapp_response_window(project, **filters)
        ignored = set(ignored_contacts or [])
        external_ids = [
            external_id
            for external_id in contacts.values_list("external_id", flat=True)
            if external_id not in ignored
        ]
        return StartFlowUseCase().execute_for_contacts(
            project, user, flow, external_ids
        )
