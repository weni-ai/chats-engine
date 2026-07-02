import logging
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone as dj_timezone
from sentry_sdk import capture_exception

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.dashboard.models import ReportStatus
from chats.apps.projects.models.models import Project
from chats.apps.rooms.models import Room
from chats.apps.rooms.services import RoomsReportService, requeue_agent_rooms
from chats.apps.rooms.usecases.build_room_export_data import BuildRoomExportData
from chats.apps.rooms.usecases.render_room_export import RenderRoomExport
from chats.apps.rooms.usecases.send_room_export_email import SendRoomExportEmail
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

    Guarded by a Redis lock so two beats can never process the same eligible
    rooms in parallel — if a previous tick still holds the lock, the new
    tick exits early and waits for the next schedule slot. The lock has a
    safety TTL so a crashed worker cannot keep the lock forever.
    """
    from django_redis import get_redis_connection

    from chats.apps.rooms.usecases.inactivity import InactivityService

    redis_conn = get_redis_connection("default")
    lock = redis_conn.lock(
        settings.INACTIVITY_TASK_LOCK_NAME,
        timeout=settings.INACTIVITY_TASK_LOCK_TIMEOUT,
    )

    acquired = lock.acquire(blocking=False)
    if not acquired:
        logger.info(
            "[INACTIVITY TASK] another execution is in progress (lock %s held), "
            "skipping this tick",
            settings.INACTIVITY_TASK_LOCK_NAME,
        )
        return

    try:
        service = InactivityService()

        try:
            warned = service.warn_inactive_rooms()
            logger.info(
                "[INACTIVITY TASK] warn_inactive_rooms processed %s rooms", warned
            )
        except Exception as exc:
            logger.exception("[INACTIVITY TASK] warn_inactive_rooms failed: %s", exc)
            capture_exception(exc)

        try:
            closed = service.close_inactive_rooms()
            logger.info(
                "[INACTIVITY TASK] close_inactive_rooms processed %s rooms", closed
            )
        except Exception as exc:
            logger.exception("[INACTIVITY TASK] close_inactive_rooms failed: %s", exc)
            capture_exception(exc)
    finally:
        try:
            lock.release()
        except Exception as exc:
            # Release can fail if the lock TTL already expired and another
            # worker re-acquired it; that is a benign race we should log but
            # not treat as fatal — the next tick will run normally.
            logger.warning(
                "[INACTIVITY TASK] failed to release lock %s: %s",
                settings.INACTIVITY_TASK_LOCK_NAME,
                exc,
            )


# ---------------------------------------------------------------------------
# Room export tasks
# ---------------------------------------------------------------------------


def _select_room_export_to_process():
    """Selects a pending/failed/stuck room export report for processing.

    Mirrors `_select_report_to_process` in the dashboard but scoped to the
    `room_export` report type, so the two flows never consume each other.
    """
    stuck_timeout = dj_timezone.now() - timedelta(minutes=10)

    with transaction.atomic():
        report = (
            ReportStatus.objects.select_for_update(skip_locked=True)
            .filter(report_type=ReportStatus.REPORT_TYPE_ROOM_EXPORT)
            .filter(
                Q(status__in=["pending", "failed"])
                | Q(status="in_progress", modified_on__lt=stuck_timeout)
            )
            .filter(retry_count__lt=ReportStatus.MAX_RETRY_COUNT)
            .order_by("created_on")
            .first()
        )
        if report:
            if report.status == "in_progress":
                logger.info(
                    "Resuming stuck room export %s (in_progress since %s)",
                    report.uuid,
                    report.modified_on,
                )
            report.status = "in_progress"
            report.save(update_fields=["status", "modified_on"])
        return report


def _process_room_export(report: ReportStatus) -> None:
    """Builds, renders and delivers a single room export report."""
    if not report.room:
        raise ValueError(
            f"ReportStatus {report.uuid} of type room_export has no associated room"
        )

    fields_config = report.fields_config or {}
    types = fields_config.get("types") or []
    if not types:
        raise ValueError(
            f"ReportStatus {report.uuid} has no export types in fields_config"
        )

    data = BuildRoomExportData().execute(report.room, generated_by=report.user.email)
    files = RenderRoomExport().execute(data, types)

    if getattr(settings, "REPORTS_SEND_EMAILS", False):
        SendRoomExportEmail().execute(
            room=report.room,
            files=files,
            recipient_email=report.user.email,
        )
    else:
        logger.info(
            "REPORTS_SEND_EMAILS disabled; skipping email for room export %s",
            report.uuid,
        )


def _handle_room_export_error(report: ReportStatus, error: Exception) -> None:
    """Updates a failed room export with retry counting and notifies on permanent failure."""
    logger.exception("Error processing pending room export: %s", error)

    report.retry_count += 1
    report.error_message = str(error)

    if report.retry_count >= ReportStatus.MAX_RETRY_COUNT:
        report.status = "permanently_failed"
        logger.warning(
            "Room export %s permanently failed after %s attempts",
            report.uuid,
            report.retry_count,
        )
    else:
        report.status = "failed"
        logger.info(
            "Room export %s failed (attempt %s/%s), will retry",
            report.uuid,
            report.retry_count,
            ReportStatus.MAX_RETRY_COUNT,
        )

    report.save()

    if report.status == "permanently_failed" and getattr(
        settings, "REPORTS_SEND_EMAILS", False
    ):
        try:
            SendRoomExportEmail().send_failure_notification(
                room=report.room,
                recipient_email=report.user.email,
                error_message=str(error),
            )
        except Exception as email_error:
            logger.exception(
                "Error sending room export failure notification: %s", email_error
            )


@app.task(name="generate_room_export")
def generate_room_export(report_status_uuid: str) -> None:
    """Generates a room export end-to-end for the given ReportStatus UUID.

    Uses ``select_for_update(skip_locked=True)`` plus a status guard so this
    synchronous task never races with ``process_pending_room_exports``: if the
    periodic worker already locked or moved the report to a non-pending state,
    this call exits early instead of double-processing it.
    """
    with transaction.atomic():
        report = (
            ReportStatus.objects.select_for_update(skip_locked=True, of=("self",))
            .select_related("room", "user", "project")
            .filter(uuid=report_status_uuid)
            .first()
        )
        if report is None:
            logger.info(
                "Room export %s is locked by another worker, skipping",
                report_status_uuid,
            )
            return

        if report.report_type != ReportStatus.REPORT_TYPE_ROOM_EXPORT:
            raise ValueError(f"ReportStatus {report.uuid} is not a room export report")

        if report.status not in ("pending", "failed"):
            logger.info(
                "Room export %s already in status=%s, skipping",
                report.uuid,
                report.status,
            )
            return

        report.status = "in_progress"
        report.save(update_fields=["status", "modified_on"])

    try:
        _process_room_export(report)
        report.status = "ready"
        report.save(update_fields=["status", "modified_on"])
        logger.info("Room export %s completed successfully", report.uuid)
    except Exception as error:
        _handle_room_export_error(report, error)
        raise


@app.task(name="process_pending_room_exports")
def process_pending_room_exports() -> None:
    """Periodic task to process pending/failed room exports."""
    report = _select_room_export_to_process()
    if not report:
        logger.info("No pending room exports to process.")
        return

    try:
        _process_room_export(report)
        report.status = "ready"
        report.save(update_fields=["status", "modified_on"])
        logger.info("Room export %s completed successfully", report.uuid)
    except Exception as error:
        _handle_room_export_error(report, error)
