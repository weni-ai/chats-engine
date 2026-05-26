"""
Helper to keep the Flows ticketer in sync when a Room is transferred between
Sectors. The Flows ticketer is bound to a Sector, so any room transfer that
changes the destination Sector must also update the ticket's ticketer in
Flows via POST /api/v2/ticket_actions.json (action=change_ticketer).

Failures are reported to Sentry and re-raised so callers can rollback the
local transfer (the local change is only valid if Flows accepts the move).
"""

import logging

from django.conf import settings
from sentry_sdk import capture_exception

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import (
    FlowRESTClient,
)
from chats.apps.rooms.exceptions import (
    FlowsChangeTicketerError,
    FlowsTicketerNotFoundError,
)
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)


def change_ticketer_for_room(
    room: Room, destination_sector_uuid: str
) -> None:
    """
    Ensure the Flows ticketer for `room` matches `destination_sector_uuid`.

    No-ops when:
      - `settings.USE_WENI_FLOWS` is False;
      - the room has no `ticket_uuid` (no Flows ticket to migrate);
      - the destination sector is the same as the current sector.

    On any failure interacting with Flows, the exception is captured in
    Sentry and re-raised so the caller can rollback the in-progress transfer.
    """
    if not getattr(settings, "USE_WENI_FLOWS", False):
        return

    if not room.ticket_uuid:
        return

    current_sector_uuid = (
        str(room.queue.sector.uuid)
        if room.queue and room.queue.sector
        else None
    )
    destination_sector_uuid = str(destination_sector_uuid)

    if current_sector_uuid == destination_sector_uuid:
        return

    project = (
        room.queue.sector.project
        if room.queue and room.queue.sector
        else None
    )
    if project is None:
        logger.error(
            "[CHANGE_TICKETER] Cannot resolve project for room %s "
            "(ticket=%s); skipping Flows ticketer update",
            room.uuid,
            room.ticket_uuid,
        )
        return

    flows_client = FlowRESTClient()

    try:
        ticketer_uuid = flows_client.get_ticketer_by_sector(
            project, destination_sector_uuid
        )
    except FlowsTicketerNotFoundError as exc:
        logger.error(
            "[CHANGE_TICKETER] Could not find ticketer for sector %s "
            "(room=%s, ticket=%s)",
            destination_sector_uuid,
            room.uuid,
            room.ticket_uuid,
            exc_info=True,
        )
        capture_exception(exc)
        raise

    try:
        flows_client.change_ticketer(
            project=project,
            ticket_uuids=[str(room.ticket_uuid)],
            ticketer_uuid=ticketer_uuid,
        )
    except FlowsChangeTicketerError as exc:
        logger.error(
            "[CHANGE_TICKETER] Flows rejected change_ticketer for room %s "
            "(ticket=%s, ticketer=%s)",
            room.uuid,
            room.ticket_uuid,
            ticketer_uuid,
            exc_info=True,
        )
        capture_exception(exc)
        raise

    logger.info(
        "[CHANGE_TICKETER] Updated Flows ticketer for room %s "
        "(ticket=%s, ticketer=%s)",
        room.uuid,
        room.ticket_uuid,
        ticketer_uuid,
    )
