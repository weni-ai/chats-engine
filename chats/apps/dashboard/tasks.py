import io
import logging
import os
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

import pandas as pd
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.db import transaction

from chats.apps.dashboard.email_templates import get_report_ready_email
from chats.apps.dashboard.models import ReportStatus, RoomMetrics
from chats.core.storages import ExcelStorage
from chats.apps.dashboard.utils import (
    calculate_first_response_time,
    calculate_last_queue_waiting_time,
    calculate_response_time,
)
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room
from chats.celery import app

logger = logging.getLogger(__name__)


def _strip_tz_value(value, project_tz=None):
    """
    Convert datetime values to project timezone (or UTC if not provided) and remove tzinfo.
    This is needed for Excel compatibility.
    """
    target_tz = project_tz if project_tz else timezone.utc
    if isinstance(value, pd.Timestamp):
        try:
            if value.tz is not None:
                return value.tz_convert(target_tz).tz_localize(None)
        except Exception:
            try:
                return value.tz_localize(None)
            except Exception:
                return pd.Timestamp(value).tz_localize(None)
        return value
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(target_tz).replace(tzinfo=None)
        return value
    return value


def _strip_tz(value, project_tz=None):
    if isinstance(value, dict):
        return {k: _strip_tz(val, project_tz) for k, val in value.items()}
    if isinstance(value, list):
        return [_strip_tz(item, project_tz) for item in value]
    return _strip_tz_value(value, project_tz)


def _excel_safe_dataframe(df: pd.DataFrame, project_tz=None) -> pd.DataFrame:
    try:
        for col in df.columns:
            df[col] = df[col].map(lambda v: _strip_tz_value(v, project_tz))
    except Exception:
        df = df.applymap(lambda v: _strip_tz_value(v, project_tz))
    return df


def _norm_file_type(raw_type: Optional[str]) -> str:
    normalized = (raw_type or "").lower()
    if "csv" in normalized:
        return "csv"
    return "xlsx"


def _get_file_extension(file_type: str) -> str:
    return "xlsx" if file_type == "xlsx" else "zip"


def _save_report_locally(report_buffer: io.BytesIO, project_uuid, timestamp: str, file_type: str):
    base_dir = getattr(
        settings,
        "REPORTS_SAVE_DIR",
        os.path.join(settings.MEDIA_ROOT, "reports"),
    )
    os.makedirs(base_dir, exist_ok=True)
    extension = _get_file_extension(file_type)
    filename = f"custom_report_{project_uuid}_{timestamp}.{extension}"
    filename = filename.replace("/", "-").replace("\\", "-")
    report_buffer.seek(0)
    file_path = os.path.join(base_dir, filename)
    with open(file_path, "wb") as f:
        f.write(report_buffer.getvalue())
    return file_path


def _send_report_email(
    project_name, project_uuid, user_email, report_buffer, timestamp, file_type, report_uuid
):
    from chats.core.storages import ReportsStorage

    reports_storage = ReportsStorage()
    extension = _get_file_extension(file_type)
    filename = f"custom_report_{project_uuid}_{timestamp}.{extension}"

    report_buffer.seek(0)
    file_path = reports_storage.save(filename, report_buffer)

    download_url = reports_storage.get_download_url(
        file_path, expiration=int(timedelta(days=7).total_seconds())
    )

    logger.info(
        "Report uploaded to S3: %s | report_uuid=%s | url=%s",
        file_path,
        report_uuid,
        download_url,
    )

    subject = f"Custom report for the project {project_name} - {timestamp}"
    message_plain, message_html = get_report_ready_email(project_name, download_url)

    email = EmailMultiAlternatives(
        subject=subject,
        body=message_plain,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
    )
    email.attach_alternative(message_html, "text/html")
    email.extra_headers = {
        "X-No-Track": "True",
        "X-Track-Click": "no",
        "o:tracking-clicks": "no",
    }
    email.send(fail_silently=False)

    logger.info(
        "Report email sent successfully to %s | report_uuid=%s",
        user_email,
        report_uuid,
    )


def _send_error_email(project_name, user_email, error_message, report_uuid):
    from chats.apps.dashboard.email_templates import get_report_failed_email

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    subject = f"Error generating custom report for project {project_name} - {timestamp}"
    message_plain, message_html = get_report_failed_email(project_name, error_message)

    email = EmailMultiAlternatives(
        subject=subject,
        body=message_plain,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
    )
    email.attach_alternative(message_html, "text/html")
    email.send(fail_silently=False)

    logger.info(
        "Error notification sent to %s | report_uuid=%s",
        user_email,
        report_uuid,
    )


def _get_parts_dir(project_uuid: UUID, report_uuid: UUID) -> str:
    """Returns the directory path for report parts."""
    return f"reports/{project_uuid}/{report_uuid}/tmp"


def _list_existing_parts(storage: ExcelStorage, parts_dir: str, prefix: str) -> List[str]:
    """Lists existing CSV parts sorted by name for a given prefix."""
    try:
        _, files = storage.listdir(parts_dir)
    except (FileNotFoundError, OSError):
        return []

    parts = sorted(
        f for f in files if f.startswith(f"{prefix}.part") and f.endswith(".csv")
    )
    return [f"{parts_dir}/{name}" for name in parts]


def _write_chunk_to_part(
    storage: ExcelStorage,
    parts_dir: str,
    part_idx: int,
    df: pd.DataFrame,
    prefix: str,
) -> None:
    """Writes a single chunk as a CSV part file, always including the header row."""
    csv_content = df.to_csv(index=False, header=True)
    part_name = f"{parts_dir}/{prefix}.part{part_idx:06d}.csv"
    storage.save(part_name, ContentFile(csv_content.encode("utf-8")))


def _write_parts_from_queryset(
    storage: ExcelStorage,
    parts_dir: str,
    queryset,
    chunk_size: int,
    completed_parts_count: int,
    prefix: str,
    project_tz=None,
    report=None,
) -> None:
    """Writes queryset data as CSV parts, resuming from completed_parts_count."""
    from django.utils import timezone as dj_timezone

    if not queryset.query.order_by:
        queryset = queryset.order_by("pk")

    total_rows = queryset.count()
    if total_rows == 0:
        return

    resume_offset = completed_parts_count * chunk_size
    part_index = completed_parts_count

    for start in range(resume_offset, total_rows, chunk_size):
        end = min(start + chunk_size, total_rows)
        logging.info(
            "Writing %s part: start=%s end=%s total=%s part_index=%s",
            prefix,
            start,
            end,
            total_rows,
            part_index,
        )
        rows = _strip_tz(list(queryset[start:end]), project_tz)
        if not rows:
            continue

        df = _excel_safe_dataframe(pd.DataFrame(rows), project_tz)
        _write_chunk_to_part(storage, parts_dir, part_index, df, prefix)
        part_index += 1

        if report is not None:
            ReportStatus.objects.filter(pk=report.pk).update(
                modified_on=dj_timezone.now()
            )


def _read_part_content(storage: ExcelStorage, part_path: str) -> str:
    """Reads content from a part file."""
    with storage.open(part_path, "rb") as f:
        return f.read().decode("utf-8")


def _combine_parts_to_sheet(
    storage: ExcelStorage,
    writer,
    part_paths: List[str],
    sheet_name: str,
    config: dict,
) -> None:
    """Combines CSV parts into an Excel sheet.

    Every part has a header row. Parts 1+ skip their header when reading
    to avoid duplicating it in the output.
    """
    if not part_paths:
        requested_fields = config.get("fields") or []
        pd.DataFrame(columns=requested_fields).to_excel(
            writer, sheet_name=sheet_name, index=False
        )
        return

    current_row = 0

    for path in part_paths:
        content = _read_part_content(storage, path)
        if not content or not content.strip():
            continue

        df = pd.read_csv(io.StringIO(content))

        if df.empty:
            continue

        is_first_write = current_row == 0
        df.to_excel(
            writer,
            sheet_name=sheet_name,
            index=False,
            header=is_first_write,
            startrow=current_row,
        )
        if is_first_write:
            current_row = 1
        current_row += len(df)


def _finalize_from_all_parts(
    storage: ExcelStorage,
    room_part_paths: List[str],
    agent_part_paths: List[str],
    file_type: str,
    rooms_config: dict,
    agent_config: dict,
    project_tz=None,
) -> bytes:
    """Finalizes report from parts of both tables."""
    if file_type == "xlsx":
        return _finalize_xlsx_from_all_parts(
            storage, room_part_paths, agent_part_paths, rooms_config, agent_config
        )
    return _finalize_csv_from_all_parts(
        storage, room_part_paths, agent_part_paths, rooms_config, agent_config
    )


def _finalize_xlsx_from_all_parts(
    storage: ExcelStorage,
    room_part_paths: List[str],
    agent_part_paths: List[str],
    rooms_config: dict,
    agent_config: dict,
) -> bytes:
    """Combines CSV parts from both tables into a final XLSX file."""
    _, xlsx_temp_path = tempfile.mkstemp(suffix=".xlsx")
    try:
        with pd.ExcelWriter(xlsx_temp_path, engine="xlsxwriter") as writer:
            if rooms_config:
                _combine_parts_to_sheet(storage, writer, room_part_paths, "rooms", rooms_config)
            if agent_config:
                _combine_parts_to_sheet(
                    storage, writer, agent_part_paths, "agent_status_logs", agent_config
                )

        with open(xlsx_temp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(xlsx_temp_path)
        except OSError:
            pass


def _stream_parts_to_csv_file(
    storage: ExcelStorage, part_paths: List[str], config: dict, destination_path: str
) -> None:
    """Reads CSV parts and streams them to the destination file.

    Parts 1+ skip their header line to avoid duplicating it in the output.
    """
    with open(destination_path, "w", encoding="utf-8") as f:
        if not part_paths:
            requested_fields = config.get("fields") or []
            if requested_fields:
                f.write(",".join(requested_fields) + "\n")
            return

        for index, path in enumerate(part_paths):
            content = _read_part_content(storage, path)
            if not content:
                continue
            if index > 0:
                newline_pos = content.find("\n")
                if newline_pos != -1:
                    content = content[newline_pos + 1:]
            f.write(content)
            if not content.endswith("\n"):
                f.write("\n")


def _finalize_csv_from_all_parts(
    storage: ExcelStorage,
    room_part_paths: List[str],
    agent_part_paths: List[str],
    rooms_config: dict,
    agent_config: dict,
) -> bytes:
    """Combines CSV parts from both tables into a final ZIP file.

    Uses temp files so only one part is held in memory at a time.
    """
    _, zip_temp_path = tempfile.mkstemp(suffix=".zip")
    csv_temp_paths = []
    try:
        with zipfile.ZipFile(zip_temp_path, "w", zipfile.ZIP_DEFLATED) as archive:
            if rooms_config:
                _, rooms_csv_path = tempfile.mkstemp(suffix=".csv")
                csv_temp_paths.append(rooms_csv_path)
                _stream_parts_to_csv_file(storage, room_part_paths, rooms_config, rooms_csv_path)
                archive.write(rooms_csv_path, "rooms.csv")

            if agent_config:
                _, agent_csv_path = tempfile.mkstemp(suffix=".csv")
                csv_temp_paths.append(agent_csv_path)
                _stream_parts_to_csv_file(storage, agent_part_paths, agent_config, agent_csv_path)
                archive.write(agent_csv_path, "agent_status_logs.csv")

        with open(zip_temp_path, "rb") as f:
            return f.read()
    finally:
        for temp_path in csv_temp_paths:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        try:
            os.unlink(zip_temp_path)
        except OSError:
            pass


def generate_metrics(room_uuid: UUID):
    """
    Generate metrics for a room.
    """

    room = Room.objects.get(uuid=room_uuid)

    metric_room = RoomMetrics.objects.get_or_create(room=room)[0]
    metric_room.message_response_time = calculate_response_time(room)

    if not room.is_active and room.first_user_assigned_at and room.ended_at:
        metric_room.interaction_time = (
            room.ended_at - room.first_user_assigned_at
        ).total_seconds()
    else:
        metric_room.interaction_time = 0

    if not room.user:
        metric_room.waiting_time += calculate_last_queue_waiting_time(room)

    metric_room.save()


@app.task(name="close_metrics")
def close_metrics(room_uuid: UUID):
    """
    Close metrics for a room.
    """
    generate_metrics(room_uuid)


@app.task(name="calculate_first_response_time_task")
def calculate_first_response_time_task(room_uuid: UUID):
    """
    Calculate and save the first response time for a room.
    Called when the agent sends their first message.
    """
    try:
        room = Room.objects.get(uuid=room_uuid)

        metric_room = RoomMetrics.objects.get_or_create(room=room)[0]

        if metric_room.first_response_time is None:
            metric_room.first_response_time = calculate_first_response_time(room)
            metric_room.save(update_fields=["first_response_time"])

            logger.info(
                f"First response time calculated for room {room_uuid}: "
                f"{metric_room.first_response_time} seconds"
            )
    except Room.DoesNotExist:
        logger.error(f"Room {room_uuid} not found when calculating first response time")
    except Exception as e:
        logger.error(
            f"Error calculating first response time for room {room_uuid}: {str(e)}"
        )


def _write_model_to_xlsx(writer, model_name: str, model_data: dict, project_tz=None):
    if not model_data:
        return
    raw_data = _strip_tz(model_data.get("data", []), project_tz)
    df = _excel_safe_dataframe(pd.DataFrame(raw_data), project_tz)
    if not df.empty:
        df.to_excel(writer, sheet_name=model_name[:31], index=False)


def _write_model_to_csv(archive, model_name: str, model_data: dict, project_tz=None):
    if not model_data:
        return
    raw_data = _strip_tz(model_data.get("data", []), project_tz)
    df = _excel_safe_dataframe(pd.DataFrame(raw_data), project_tz)
    if not df.empty:
        archive.writestr(f"{model_name[:31]}.csv", df.to_csv(index=False).encode("utf-8"))


@app.task
def generate_custom_fields_report(
    project_uuid: UUID, fields_config: dict, user_email: str, report_status_id: UUID
):
    """
    Generate a custom report based on the fields configuration.
    """
    from chats.apps.api.v1.dashboard.presenter import ModelFieldsPresenter
    from chats.apps.api.v1.dashboard.viewsets import ReportFieldsValidatorViewSet

    project = Project.objects.get(uuid=project_uuid)
    project_tz = project.timezone
    report_validator = ReportFieldsValidatorViewSet()
    report_status = ReportStatus.objects.get(uuid=report_status_id)

    try:
        report_status.status = "in_progress"
        report_status.save()

        available_fields = ModelFieldsPresenter.get_models_info()
        models_config = {
            key: value for key, value in (fields_config or {}).items() if key in available_fields
        }
        report_data = report_validator._generate_report_data(models_config, project)

        file_type = _norm_file_type(fields_config.get("_file_type"))
        report_buffer = io.BytesIO()

        if file_type == "xlsx":
            with pd.ExcelWriter(report_buffer, engine="xlsxwriter") as writer:
                for model_name in ["rooms", "agent_status_logs"]:
                    _write_model_to_xlsx(
                        writer, model_name, report_data.get(model_name, {}), project_tz
                    )
        else:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for model_name in ["rooms", "agent_status_logs"]:
                    _write_model_to_csv(
                        archive, model_name, report_data.get(model_name, {}), project_tz
                    )
            report_buffer = zip_buffer

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

        if getattr(settings, "REPORTS_SAVE_LOCALLY", True):
            file_path = _save_report_locally(report_buffer, project.uuid, timestamp, file_type)
            logger.info("Custom report saved at: %s", file_path)

        if getattr(settings, "REPORTS_SEND_EMAILS", False):
            try:
                from chats.core.storages import ReportsStorage

                storage = ReportsStorage()
                ext = "xlsx" if file_type == "xlsx" else "zip"
                filename = f"custom_report_{project.uuid}_{dt}.{ext}"

                output.seek(0)
                file_path = storage.save(filename, output)

                download_url = storage.get_download_url(
                    file_path, expiration=int(timedelta(days=7).total_seconds())
                )

                logger.info(
                    "Report uploaded to S3: %s | report_uuid=%s | url=%s",
                    file_path,
                    report_status.uuid,
                    download_url,
                )

                subject = f"Custom report for the project {project.name} - {dt}"
                message_plain, message_html = get_report_ready_email(
                    project.name, download_url
                )

                email = EmailMultiAlternatives(
                    subject=subject,
                    body=message_plain,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user_email],
                )
                email.attach_alternative(message_html, "text/html")
                email.extra_headers = {
                    "X-No-Track": "True",
                    "X-Track-Click": "no",
                    "o:tracking-clicks": "no",
                }

                email.send(fail_silently=False)

                logger.info(
                    "Report email sent successfully to %s | report_uuid=%s",
                    user_email,
                    report_buffer,
                    timestamp,
                    file_type,
                    report_status.uuid,
                )
            except Exception as e:
                logger.exception("Error sending email report: %s", e)

        report_status.status = "ready"
        report_status.save()

    except Exception as e:
        report_status.status = "failed"
        report_status.error_message = str(e)
        report_status.save()

        if getattr(settings, "REPORTS_SEND_EMAILS", False):
            try:
                _send_error_email(project.name, user_email, str(e), report_status.uuid)
            except Exception as email_error:
                logger.exception(
                    "Error sending error notification email: %s", email_error
                )

        raise


def _select_report_to_process():
    """Selects a pending, failed, or stuck in_progress report for processing."""
    from django.db.models import Q
    from django.utils import timezone as dj_timezone

    stuck_timeout = dj_timezone.now() - timedelta(minutes=10)

    with transaction.atomic():
        report = (
            ReportStatus.objects.select_for_update(skip_locked=True)
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
                logging.info(
                    "Resuming stuck report %s (in_progress since %s)",
                    report.uuid,
                    report.modified_on,
                )
            report.status = "in_progress"
            report.save()
        return report


def _cleanup_parts(storage: ExcelStorage, parts_dir: str) -> None:
    """Removes temporary part files after successful report generation."""
    try:
        # Cleanup both rooms and agent_status_logs parts
        for prefix in ["rooms", "agent_status_logs"]:
            parts = _list_existing_parts(storage, parts_dir, prefix)
            for part_path in parts:
                try:
                    storage.delete(part_path)
                except Exception:
                    pass
        # Try to remove the directory itself
        try:
            storage.delete(parts_dir)
        except Exception:
            pass
        logging.info("Cleaned up temporary parts from %s", parts_dir)
    except Exception as e:
        logging.warning("Failed to cleanup parts directory %s: %s", parts_dir, e)


def _process_report_with_resume(report, report_validator, available_fields, project_tz):
    """Processes report with resume capability using parts for both tables."""
    fields_config = report.fields_config or {}
    file_type = _norm_file_type(fields_config.get("type"))
    chunk_size = getattr(settings, "REPORTS_CHUNK_SIZE", 5000)

    storage = ExcelStorage()
    parts_dir = _get_parts_dir(report.project.uuid, report.uuid)

    rooms_config = fields_config.get("rooms") or {}
    if rooms_config.get("fields") and "rooms" in available_fields:
        processed = report_validator._process_model_fields(
            "rooms", rooms_config, report.project, available_fields
        )
        rooms_queryset = (processed or {}).get("queryset")

        if rooms_queryset is not None:
            completed_room_parts = _list_existing_parts(storage, parts_dir, "rooms")
            completed_room_count = len(completed_room_parts)

            if completed_room_count > 0:
                logging.info(
                    "Resuming report %s rooms from part %s", report.uuid, completed_room_count
                )

            _write_parts_from_queryset(
                storage, parts_dir, rooms_queryset, chunk_size,
                completed_room_count, "rooms", project_tz,
                report=report,
            )

    agent_config = fields_config.get("agent_status_logs") or {}
    if agent_config.get("fields") and "agent_status_logs" in available_fields:
        processed = report_validator._process_model_fields(
            "agent_status_logs", agent_config, report.project, available_fields
        )
        agent_queryset = (processed or {}).get("queryset")

        if agent_queryset is not None:
            completed_agent_parts = _list_existing_parts(storage, parts_dir, "agent_status_logs")
            completed_agent_count = len(completed_agent_parts)

            if completed_agent_count > 0:
                logging.info(
                    "Resuming report %s agent_status_logs from part %s",
                    report.uuid,
                    completed_agent_count,
                )

            _write_parts_from_queryset(
                storage, parts_dir, agent_queryset, chunk_size,
                completed_agent_count, "agent_status_logs", project_tz,
                report=report,
            )

    room_part_paths = _list_existing_parts(storage, parts_dir, "rooms")
    agent_part_paths = _list_existing_parts(storage, parts_dir, "agent_status_logs")

    final_bytes = _finalize_from_all_parts(
        storage, room_part_paths, agent_part_paths, file_type,
        rooms_config, agent_config, project_tz,
    )

    _cleanup_parts(storage, parts_dir)

    return io.BytesIO(final_bytes), file_type


def _save_and_send_report(report, report_buffer, file_type, user_email):
    """Saves report locally and sends email if configured."""
    project = report.project
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

    if getattr(settings, "REPORTS_SAVE_LOCALLY", True):
        file_path = _save_report_locally(report_buffer, project.uuid, timestamp, file_type)
        logging.info(
            "Custom report saved at: %s | report_uuid=%s", file_path, report.uuid
        )

    logging.info("Processing report %s for project %s done.", report.uuid, project.uuid)

    if getattr(settings, "REPORTS_SEND_EMAILS", False):
        try:
            _send_report_email(
                project.name,
                project.uuid,
                user_email,
                report_buffer,
                timestamp,
                file_type,
                report.uuid,
            )
        except Exception as e:
            logging.exception("Error sending email report: %s", e)


def _handle_report_error(report, error, user_email):
    """Handles report processing error with retry counting."""
    logging.exception("Error processing pending report: %s", error)

    report.retry_count += 1
    report.error_message = str(error)

    if report.retry_count >= ReportStatus.MAX_RETRY_COUNT:
        report.status = "permanently_failed"
        logging.warning(
            "Report %s permanently failed after %s attempts",
            report.uuid,
            report.retry_count,
        )
        try:
            storage = ExcelStorage()
            parts_dir = _get_parts_dir(report.project.uuid, report.uuid)
            _cleanup_parts(storage, parts_dir)
        except Exception:
            logging.warning("Failed to cleanup parts for permanently failed report %s", report.uuid)
    else:
        report.status = "failed"
        logging.info(
            "Report %s failed (attempt %s/%s), will retry",
            report.uuid,
            report.retry_count,
            ReportStatus.MAX_RETRY_COUNT,
        )

    report.save()

    # Only send error email on permanent failure
    if report.status == "permanently_failed" and getattr(
        settings, "REPORTS_SEND_EMAILS", False
    ):
        try:
            _send_error_email(report.project.name, user_email, str(error), report.uuid)
        except Exception as email_error:
            logging.exception("Error sending error notification email: %s", email_error)


@app.task(name="process_pending_reports")
def process_pending_reports():
    """
    Periodic task to process pending/failed reports with resume capability.
    """
    from chats.apps.api.v1.dashboard.presenter import ModelFieldsPresenter
    from chats.apps.api.v1.dashboard.viewsets import ReportFieldsValidatorViewSet

    report = _select_report_to_process()
    if not report:
        logging.info("No pending reports to process.")
        return

    project_tz = report.project.timezone
    user_email = report.user.email

    try:
        report_validator = ReportFieldsValidatorViewSet()
        available_fields = ModelFieldsPresenter.get_models_info()

        report_buffer, file_type = _process_report_with_resume(
            report, report_validator, available_fields, project_tz
        )

        _save_and_send_report(report, report_buffer, file_type, user_email)

        report.status = "ready"
        report.save()

    except Exception as e:
        _handle_report_error(report, e, user_email)
