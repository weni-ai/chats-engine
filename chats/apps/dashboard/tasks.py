import io
import logging
import os
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


def _strip_tz_value(v, project_tz=None):
    """
    Convert datetime values to project timezone (or UTC if not provided) and remove tzinfo.
    This is needed for Excel compatibility.
    """
    target_tz = project_tz if project_tz else timezone.utc
    if isinstance(v, pd.Timestamp):
        try:
            if v.tz is not None:
                return v.tz_convert(target_tz).tz_localize(None)
        except Exception:
            try:
                return v.tz_localize(None)
            except Exception:
                return pd.Timestamp(v).tz_localize(None)
        return v
    if isinstance(v, datetime):
        if v.tzinfo is not None:
            return v.astimezone(target_tz).replace(tzinfo=None)
        return v
    return v


def _strip_tz(obj, project_tz=None):
    if isinstance(obj, dict):
        return {k: _strip_tz(v, project_tz) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_tz(v, project_tz) for v in obj]
    return _strip_tz_value(obj, project_tz)


def _excel_safe_dataframe(df: pd.DataFrame, project_tz=None) -> pd.DataFrame:
    try:
        for col in df.columns:
            df[col] = df[col].map(lambda v: _strip_tz_value(v, project_tz))
    except Exception:
        df = df.applymap(lambda v: _strip_tz_value(v, project_tz))
    return df


def _norm_file_type(v: Optional[str]) -> str:
    v = (v or "").lower()
    if "csv" in v:
        return "csv"
    return "xlsx"


def _get_file_extension(file_type: str) -> str:
    return "xlsx" if file_type == "xlsx" else "zip"


def _save_report_locally(output: io.BytesIO, project_uuid, dt: str, file_type: str):
    base_dir = getattr(
        settings,
        "REPORTS_SAVE_DIR",
        os.path.join(settings.MEDIA_ROOT, "reports"),
    )
    os.makedirs(base_dir, exist_ok=True)
    ext = _get_file_extension(file_type)
    filename = f"custom_report_{project_uuid}_{dt}.{ext}"
    filename = filename.replace("/", "-").replace("\\", "-")
    output.seek(0)
    file_path = os.path.join(base_dir, filename)
    with open(file_path, "wb") as f:
        f.write(output.getvalue())
    return file_path


def _send_report_email(
    project_name, project_uuid, user_email, output, dt, file_type, report_uuid
):
    from chats.core.storages import ReportsStorage

    storage = ReportsStorage()
    ext = _get_file_extension(file_type)
    filename = f"custom_report_{project_uuid}_{dt}.{ext}"

    output.seek(0)
    file_path = storage.save(filename, output)

    download_url = storage.get_download_url(
        file_path, expiration=int(timedelta(days=7).total_seconds())
    )

    logger.info(
        "Report uploaded to S3: %s | report_uuid=%s | url=%s",
        file_path,
        report_uuid,
        download_url,
    )

    subject = f"Custom report for the project {project_name} - {dt}"
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

    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    subject = f"Error generating custom report for project {project_name} - {dt}"
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


def _get_chunk_size(total_records: int) -> int:
    base_chunk_size = getattr(settings, "REPORTS_CHUNK_SIZE", 5000)
    return (
        base_chunk_size * 2
        if total_records > (base_chunk_size * 10)
        else base_chunk_size
    )


def _get_parts_dir(project_uuid: UUID, report_uuid: UUID) -> str:
    """Returns the directory path for report parts."""
    return f"reports/{project_uuid}/{report_uuid}/tmp"


def _list_existing_parts(storage: ExcelStorage, parts_dir: str, prefix: str) -> List[str]:
    """Lists existing CSV parts sorted by name for a given prefix."""
    try:
        _, files = storage.listdir(parts_dir)
    except Exception:
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
    include_header: bool,
    prefix: str,
) -> None:
    """Writes a single chunk as a CSV part file."""
    csv_content = df.to_csv(index=False, header=include_header)
    part_name = f"{parts_dir}/{prefix}.part{part_idx:06d}.csv"
    storage.save(part_name, ContentFile(csv_content.encode("utf-8")))


def _write_parts_from_queryset(
    storage: ExcelStorage,
    parts_dir: str,
    qs,
    chunk_size: int,
    existing_count: int,
    prefix: str,
    project_tz=None,
) -> None:
    """Writes queryset data as CSV parts, resuming from existing_count."""
    total = qs.count()
    if total == 0:
        return

    next_start = existing_count * chunk_size
    part_idx = existing_count
    header_written = existing_count > 0

    for start in range(next_start, total, chunk_size):
        end = min(start + chunk_size, total)
        logging.info(
            "Writing %s part: start=%s end=%s total=%s part_idx=%s",
            prefix,
            start,
            end,
            total,
            part_idx,
        )
        chunk = _strip_tz(list(qs[start:end]), project_tz)
        if not chunk:
            continue

        df = _excel_safe_dataframe(pd.DataFrame(chunk), project_tz)
        _write_chunk_to_part(storage, parts_dir, part_idx, df, not header_written, prefix)
        header_written = True
        part_idx += 1


def _read_part_content(storage: ExcelStorage, part_path: str) -> str:
    """Reads content from a part file."""
    with storage.open(part_path, "rb") as f:
        return f.read().decode("utf-8")


def _finalize_xlsx_from_parts(
    storage: ExcelStorage, parts: List[str], rooms_cfg: dict
) -> bytes:
    """Combines CSV parts into a final XLSX file."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        if not parts:
            requested_fields = rooms_cfg.get("fields") or []
            pd.DataFrame(columns=requested_fields).to_excel(
                writer, sheet_name="rooms", index=False
            )
            return output.getvalue()

        current_row = 0
        for idx, part_path in enumerate(parts):
            content = _read_part_content(storage, part_path)
            if not content or not content.strip():
                continue

            # Skip header for non-first parts
            if idx > 0 and "\n" in content:
                content = content.split("\n", 1)[1]
            if not content.strip():
                continue

            df = pd.read_csv(io.StringIO(content))
            if df.empty:
                continue

            df.to_excel(
                writer,
                sheet_name="rooms",
                index=False,
                header=(current_row == 0),
                startrow=current_row if current_row > 0 else 0,
            )
            current_row += len(df)

    output.seek(0)
    return output.getvalue()


def _finalize_csv_from_parts(
    storage: ExcelStorage, parts: List[str], rooms_cfg: dict
) -> bytes:
    """Combines CSV parts into a final CSV file."""
    combined = io.StringIO()

    if not parts:
        requested_fields = rooms_cfg.get("fields") or []
        if requested_fields:
            combined.write(",".join(requested_fields) + "\n")
        return combined.getvalue().encode("utf-8")

    for idx, part_path in enumerate(parts):
        content = _read_part_content(storage, part_path)
        if not content:
            continue

        if idx == 0:
            combined.write(content)
        else:
            # Skip header for non-first parts
            content = content.split("\n", 1)[1] if "\n" in content else ""
            combined.write(content)

    return combined.getvalue().encode("utf-8")


def _finalize_from_parts(
    storage: ExcelStorage, parts: List[str], file_type: str, rooms_cfg: dict
) -> bytes:
    """Finalizes report from parts based on file type."""
    if file_type == "xlsx":
        return _finalize_xlsx_from_parts(storage, parts, rooms_cfg)
    return _finalize_csv_from_parts(storage, parts, rooms_cfg)


def _combine_parts_to_sheet(
    storage: ExcelStorage,
    writer,
    parts: List[str],
    sheet_name: str,
    cfg: dict,
) -> None:
    """Combines CSV parts into an Excel sheet."""
    if not parts:
        requested_fields = cfg.get("fields") or []
        pd.DataFrame(columns=requested_fields).to_excel(
            writer, sheet_name=sheet_name, index=False
        )
        return

    current_row = 0
    for idx, part_path in enumerate(parts):
        content = _read_part_content(storage, part_path)
        if not content or not content.strip():
            continue

        if idx > 0 and "\n" in content:
            content = content.split("\n", 1)[1]
        if not content.strip():
            continue

        df = pd.read_csv(io.StringIO(content))
        if df.empty:
            continue

        df.to_excel(
            writer,
            sheet_name=sheet_name,
            index=False,
            header=(current_row == 0),
            startrow=current_row if current_row > 0 else 0,
        )
        current_row += len(df)


def _combine_parts_to_csv(
    storage: ExcelStorage,
    parts: List[str],
    cfg: dict,
) -> str:
    """Combines CSV parts into a single CSV string."""
    combined = io.StringIO()

    if not parts:
        requested_fields = cfg.get("fields") or []
        if requested_fields:
            combined.write(",".join(requested_fields) + "\n")
        return combined.getvalue()

    for idx, part_path in enumerate(parts):
        content = _read_part_content(storage, part_path)
        if not content:
            continue

        if idx == 0:
            combined.write(content)
        else:
            content = content.split("\n", 1)[1] if "\n" in content else ""
            combined.write(content)

    return combined.getvalue()


def _finalize_from_all_parts(
    storage: ExcelStorage,
    rooms_parts: List[str],
    agent_parts: List[str],
    file_type: str,
    rooms_cfg: dict,
    agent_status_cfg: dict,
    project_tz=None,
) -> bytes:
    """Finalizes report from parts of both tables."""
    if file_type == "xlsx":
        return _finalize_xlsx_from_all_parts(
            storage, rooms_parts, agent_parts, rooms_cfg, agent_status_cfg
        )
    return _finalize_csv_from_all_parts(
        storage, rooms_parts, agent_parts, rooms_cfg, agent_status_cfg
    )


def _finalize_xlsx_from_all_parts(
    storage: ExcelStorage,
    rooms_parts: List[str],
    agent_parts: List[str],
    rooms_cfg: dict,
    agent_status_cfg: dict,
) -> bytes:
    """Combines CSV parts from both tables into a final XLSX file."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Write rooms sheet
        if rooms_cfg:
            _combine_parts_to_sheet(storage, writer, rooms_parts, "rooms", rooms_cfg)

        # Write agent_status_logs sheet
        if agent_status_cfg:
            _combine_parts_to_sheet(
                storage, writer, agent_parts, "agent_status_logs", agent_status_cfg
            )

    output.seek(0)
    return output.getvalue()


def _finalize_csv_from_all_parts(
    storage: ExcelStorage,
    rooms_parts: List[str],
    agent_parts: List[str],
    rooms_cfg: dict,
    agent_status_cfg: dict,
) -> bytes:
    """Combines CSV parts from both tables into a final ZIP file."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write rooms CSV
        if rooms_cfg:
            rooms_csv = _combine_parts_to_csv(storage, rooms_parts, rooms_cfg)
            zf.writestr("rooms.csv", rooms_csv.encode("utf-8"))

        # Write agent_status_logs CSV
        if agent_status_cfg:
            agent_csv = _combine_parts_to_csv(storage, agent_parts, agent_status_cfg)
            zf.writestr("agent_status_logs.csv", agent_csv.encode("utf-8"))

    zip_buf.seek(0)
    return zip_buf.getvalue()


def generate_metrics(room_uuid: UUID):
    """
    Generate metrics for a room.
    """

    room = Room.objects.get(uuid=room_uuid)

    interaction_time = room.ended_at - room.created_on

    metric_room = RoomMetrics.objects.get_or_create(room=room)[0]
    metric_room.message_response_time = calculate_response_time(room)
    metric_room.interaction_time = interaction_time.total_seconds()

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
    df_data = _strip_tz(model_data.get("data", []), project_tz)
    df = pd.DataFrame(df_data)
    df = _excel_safe_dataframe(df, project_tz)
    if not df.empty:
        df.to_excel(writer, sheet_name=model_name[:31], index=False)


def _write_model_to_csv(zf, model_name: str, model_data: dict, project_tz=None):
    if not model_data:
        return
    df_data = _strip_tz(model_data.get("data", []), project_tz)
    df = pd.DataFrame(df_data)
    df = _excel_safe_dataframe(df, project_tz)
    if not df.empty:
        zf.writestr(f"{model_name[:31]}.csv", df.to_csv(index=False).encode("utf-8"))


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
    report_generator = ReportFieldsValidatorViewSet()
    report_status = ReportStatus.objects.get(uuid=report_status_id)

    try:
        report_status.status = "in_progress"
        report_status.save()

        available_fields = ModelFieldsPresenter.get_models_info()
        models_config = {
            k: v for k, v in (fields_config or {}).items() if k in available_fields
        }
        report_data = report_generator._generate_report_data(models_config, project)

        file_type = _norm_file_type(fields_config.get("_file_type"))
        output = io.BytesIO()

        if file_type == "xlsx":
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                for model_name in ["rooms", "agent_status_logs"]:
                    _write_model_to_xlsx(
                        writer, model_name, report_data.get(model_name, {}), project_tz
                    )
        else:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for model_name in ["rooms", "agent_status_logs"]:
                    _write_model_to_csv(
                        zf, model_name, report_data.get(model_name, {}), project_tz
                    )
            output = zip_buf

        dt = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

        if getattr(settings, "REPORTS_SAVE_LOCALLY", True):
            file_path = _save_report_locally(output, project.uuid, dt, file_type)
            logger.info("Custom report saved at: %s", file_path)

        if getattr(settings, "REPORTS_SEND_EMAILS", False):
            try:
                _send_report_email(
                    project.name,
                    project.uuid,
                    user_email,
                    output,
                    dt,
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


def _write_xlsx_chunks(
    writer, sheet_name: str, qs, chunk_size: int, model_cfg: dict, project_tz=None
):
    if qs is None:
        pd.DataFrame().to_excel(writer, sheet_name=sheet_name[:31], index=False)
        return

    if qs.count() == 0:
        requested_fields = model_cfg.get("fields") or []
        pd.DataFrame(columns=requested_fields).to_excel(
            writer, sheet_name=sheet_name[:31], index=False
        )
        return

    total = qs.count()
    row_offset = 0
    for start in range(0, total, chunk_size):
        end = min(start + chunk_size, total)
        logging.info(
            "Writing chunk: sheet=%s start=%s end=%s total=%s",
            sheet_name,
            start,
            end,
            total,
        )
        chunk = _strip_tz(list(qs[start:end]), project_tz)
        if not chunk:
            continue
        df = _excel_safe_dataframe(pd.DataFrame(chunk), project_tz)
        df.to_excel(
            writer,
            sheet_name=sheet_name[:31],
            index=False,
            header=(row_offset == 0),
            startrow=row_offset or 0,
        )
        row_offset += len(df)


def _write_csv_chunks(csv_buffers: dict, sheet_name: str, qs, project_tz=None):
    total = qs.count()
    chunk_size = _get_chunk_size(total)
    buf = csv_buffers.get(sheet_name) or io.StringIO()
    csv_buffers[sheet_name] = buf

    row_offset = 0
    for start in range(0, total, chunk_size):
        end = min(start + chunk_size, total)
        logging.info(
            "Writing chunk (csv): sheet=%s start=%s end=%s total=%s",
            sheet_name,
            start,
            end,
            total,
        )
        chunk = _strip_tz(list(qs[start:end]), project_tz)
        if not chunk:
            continue
        df = _excel_safe_dataframe(pd.DataFrame(chunk), project_tz)
        df.to_csv(buf, index=False, header=(row_offset == 0))
        row_offset += len(df)


def _process_xlsx_report(
    view, fields_config, project, available_fields, output, project_tz=None
):
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for model_name in ["rooms", "agent_status_logs"]:
            model_cfg = fields_config.get(model_name) or {}
            if not model_cfg or model_name not in available_fields:
                continue

            query_data = view._process_model_fields(
                model_name, model_cfg, project, available_fields
            )
            qs = (query_data or {}).get("queryset")
            total_records = qs.count() if qs is not None else 0
            chunk_size = _get_chunk_size(total_records)
            logging.info(
                "Report size for %s: %s records, chunk_size: %s",
                model_name,
                total_records,
                chunk_size,
            )
            _write_xlsx_chunks(
                writer, model_name, qs, chunk_size, model_cfg, project_tz
            )


def _process_csv_report(
    view, fields_config, project, available_fields, project_tz=None
):
    csv_buffers = {}
    for model_name in ["rooms", "agent_status_logs"]:
        if model_name in fields_config and model_name in available_fields:
            query_data = view._process_model_fields(
                model_name, fields_config[model_name], project, available_fields
            )
            if "queryset" in (query_data or {}):
                _write_csv_chunks(
                    csv_buffers, model_name, query_data["queryset"], project_tz
                )

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for sheet_name, buf in csv_buffers.items():
            zf.writestr(f"{sheet_name[:31]}.csv", buf.getvalue().encode("utf-8"))
    return zip_buf


def _select_report_to_process():
    """Selects a pending or failed report for processing (with retry limit)."""
    with transaction.atomic():
        report = (
            ReportStatus.objects.select_for_update(skip_locked=True)
            .filter(status__in=["pending", "failed"])
            .filter(retry_count__lt=ReportStatus.MAX_RETRY_COUNT)
            .order_by("created_on")
            .first()
        )
        if report:
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


def _process_report_with_resume(report, view, available_fields, project_tz):
    """Processes report with resume capability using parts for both tables."""
    fields_config = report.fields_config or {}
    file_type = _norm_file_type(fields_config.get("type"))
    chunk_size = getattr(settings, "REPORTS_CHUNK_SIZE", 5000)

    storage = ExcelStorage()
    parts_dir = _get_parts_dir(report.project.uuid, report.uuid)

    # Process rooms with resume
    rooms_cfg = fields_config.get("rooms") or {}
    if rooms_cfg and "rooms" in available_fields:
        query_data = view._process_model_fields(
            "rooms", rooms_cfg, report.project, available_fields
        )
        rooms_qs = (query_data or {}).get("queryset")

        if rooms_qs is not None:
            existing_rooms_parts = _list_existing_parts(storage, parts_dir, "rooms")
            existing_rooms_count = len(existing_rooms_parts)

            if existing_rooms_count > 0:
                logging.info(
                    "Resuming report %s rooms from part %s", report.uuid, existing_rooms_count
                )

            _write_parts_from_queryset(
                storage, parts_dir, rooms_qs, chunk_size, existing_rooms_count, "rooms", project_tz
            )

    # Process agent_status_logs with resume
    agent_status_cfg = fields_config.get("agent_status_logs") or {}
    if agent_status_cfg and "agent_status_logs" in available_fields:
        query_data = view._process_model_fields(
            "agent_status_logs", agent_status_cfg, report.project, available_fields
        )
        agent_qs = (query_data or {}).get("queryset")

        if agent_qs is not None:
            existing_agent_parts = _list_existing_parts(storage, parts_dir, "agent_status_logs")
            existing_agent_count = len(existing_agent_parts)

            if existing_agent_count > 0:
                logging.info(
                    "Resuming report %s agent_status_logs from part %s",
                    report.uuid,
                    existing_agent_count,
                )

            _write_parts_from_queryset(
                storage, parts_dir, agent_qs, chunk_size, existing_agent_count, "agent_status_logs", project_tz
            )

    # Get all parts for finalization
    rooms_parts = _list_existing_parts(storage, parts_dir, "rooms")
    agent_parts = _list_existing_parts(storage, parts_dir, "agent_status_logs")

    # Generate final output
    final_bytes = _finalize_from_all_parts(
        storage, rooms_parts, agent_parts, file_type, rooms_cfg, agent_status_cfg, project_tz
    )

    # Cleanup temporary parts
    _cleanup_parts(storage, parts_dir)

    return io.BytesIO(final_bytes), file_type


def _save_and_send_report(report, output, file_type, user_email):
    """Saves report locally and sends email if configured."""
    project = report.project
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

    if getattr(settings, "REPORTS_SAVE_LOCALLY", True):
        file_path = _save_report_locally(output, project.uuid, dt, file_type)
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
                output,
                dt,
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
        view = ReportFieldsValidatorViewSet()
        available_fields = ModelFieldsPresenter.get_models_info()

        output, file_type = _process_report_with_resume(
            report, view, available_fields, project_tz
        )

        _save_and_send_report(report, output, file_type, user_email)

        report.status = "ready"
        report.save()

    except Exception as e:
        _handle_report_error(report, e, user_email)
