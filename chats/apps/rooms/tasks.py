import logging
from uuid import UUID

from sentry_sdk import capture_exception

from chats.apps.projects.models.models import Project
from chats.apps.rooms.models import Room
from chats.apps.rooms.services import requeue_agent_rooms, RoomsReportService
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.celery import app

logger = logging.getLogger(__name__)


@app.task
def requeue_agent_rooms_task(user_email: str, project_uuid: str):
    rooms = Room.objects.filter(
        user__email=user_email,
        queue__sector__project__uuid=project_uuid,
        is_active=True,
    )
    requeue_agent_rooms(rooms)


@app.task
def generate_rooms_report(project_uuid: UUID, filters: dict, recipient_email: str):
    """
    Generate a report of the rooms in the project.
    """
    project = Project.objects.get(uuid=project_uuid)

    report_service = RoomsReportService(project)
    report_service.generate_report(filters, recipient_email)


@app.task
def update_ticket_assignee_async(room_uuid: str, ticket_uuid: str, user_email: str):
    """
    Asynchronously update ticket assignee in the external Flows API.

    Args:
        room_uuid (str): UUID of the room being processed
        ticket_uuid (str): UUID of the ticket to update
        user_email (str): Email of the user to assign to the ticket

    Returns:
        dict: Result of the operation with status and details
    """
    logger.info(
        f"[TASK] Starting ticket assignee update - Room: {room_uuid}, "
        f"Ticket: {ticket_uuid}, User: {user_email}"
    )

    try:
        flows_client = FlowRESTClient()

        flows_client.update_ticket_assignee(ticket_uuid, user_email)

        logger.info(
            f"[TASK] Successfully updated ticket assignee - Room: {room_uuid}, "
            f"Ticket: {ticket_uuid}, User: {user_email}"
        )

        return {
            "status": "success",
            "room_uuid": room_uuid,
            "ticket_uuid": ticket_uuid,
            "user_email": user_email,
        }

    except Exception as exc:
        logger.error(
            f"[TASK] Error updating ticket assignee - Room: {room_uuid}, "
            f"Ticket: {ticket_uuid}, User: {user_email}, "
            f"Error: {str(exc)}"
        )

        raise exc


@app.task(name="check_inactivity_rooms")
def check_inactivity_rooms():
    """
    Periodic Celery beat task that drives the inactivity feature.

    Runs `warn_inactive_rooms` and `close_inactive_rooms` every tick. Each
    step is wrapped in its own try/except so that a failure in the warning
    pass does not prevent the closure pass from executing on this tick.
    """
    from chats.apps.rooms.usecases.inactivity import InactivityService

    service = InactivityService()

    try:
        warned = service.warn_inactive_rooms()
        logger.info("[INACTIVITY TASK] warn_inactive_rooms processed %s rooms", warned)
    except Exception as exc:
        logger.exception("[INACTIVITY TASK] warn_inactive_rooms failed: %s", exc)
        capture_exception(exc)

    try:
        closed = service.close_inactive_rooms()
        logger.info("[INACTIVITY TASK] close_inactive_rooms processed %s rooms", closed)
    except Exception as exc:
        logger.exception("[INACTIVITY TASK] close_inactive_rooms failed: %s", exc)
        capture_exception(exc)
