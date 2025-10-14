import io
import logging
import os
import zipfile
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import pandas as pd
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction

from chats.apps.dashboard.models import ReportStatus, RoomMetrics
from chats.apps.dashboard.utils import (
    calculate_last_queue_waiting_time,
    calculate_response_time,
    calculate_first_response_time,
)
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room
from chats.celery import app

logger = logging.getLogger(__name__)


def _strip_tz_value(v):
    if isinstance(v, pd.Timestamp):
        try:
            if v.tz is not None:
                return v.tz_convert("UTC").tz_localize(None)
        except Exception:
            try:
                return v.tz_localize(None)
            except Exception:
                return pd.Timestamp(v).tz_localize(None)
        return v
    if isinstance(v, datetime):
        if v.tzinfo is not None:
            return v.astimezone(timezone.utc).replace(tzinfo=None)
        return v
    return v


def _strip_tz(obj):
    if isinstance(obj, dict):
        return {k: _strip_tz(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_tz(v) for v in obj]
    return _strip_tz_value(obj)


def _excel_safe_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    try:
        for col in df.columns:
            df[col] = df[col].map(_strip_tz_value)
    except Exception:
        df = df.applymap(_strip_tz_value)
    return df


def _norm_file_type(v: Optional[str]) -> str:
    v = (v or "").lower()
    if "csv" in v:
        return "csv"
    return "xlsx"


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
            metric_room.save(update_fields=['first_response_time'])
            
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


@app.task
def generate_custom_fields_report(
    project_uuid: UUID, fields_config: dict, user_email: str, report_status_id: UUID
):
    """
    Generate a custom report based on the fields configuration.
    """
    from chats.apps.api.v1.dashboard.viewsets import ReportFieldsValidatorViewSet

    project = Project.objects.get(uuid=project_uuid)
    report_generator = ReportFieldsValidatorViewSet()

    # Search the status object
    report_status = ReportStatus.objects.get(uuid=report_status_id)

    try:
        # Update to processing
        report_status.status = "processing"
        report_status.save()

        # Generate the report: filter only known models and ignore auxiliary keys (ex.: 'type')
        from chats.apps.api.v1.dashboard.presenter import ModelFieldsPresenter

        available_fields = ModelFieldsPresenter.get_models_info()
        models_config = {
            k: v for k, v in (fields_config or {}).items() if k in available_fields
        }
        report_data = report_generator._generate_report_data(models_config, project)

        # Generate in XLSX (default) or CSV+ZIP
        file_type = _norm_file_type(fields_config.get("_file_type"))
        output = io.BytesIO()
        if file_type == "xlsx":
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                # Write only the rooms sheet
                model_data = report_data.get("rooms", {})
                df_data = _strip_tz(model_data.get("data", []))
                df = pd.DataFrame(df_data)
                df = _excel_safe_dataframe(df)
                if not df.empty:
                    df.to_excel(writer, sheet_name="rooms", index=False)
        else:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                df_data = _strip_tz(report_data.get("rooms", {}).get("data", []))
                df = pd.DataFrame(df_data)
                df = _excel_safe_dataframe(df)
                if not df.empty:
                    zf.writestr("rooms.csv", df.to_csv(index=False).encode("utf-8"))
            output = zip_buf

        dt = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        if getattr(settings, "REPORTS_SAVE_LOCALLY", True):
            base_dir = getattr(
                settings,
                "REPORTS_SAVE_DIR",
                os.path.join(settings.MEDIA_ROOT, "reports"),
            )
            os.makedirs(base_dir, exist_ok=True)
            ext = "xlsx" if file_type == "xlsx" else "zip"
            filename = f"custom_report_{project.uuid}_{dt}.{ext}"
            filename = filename.replace("/", "-").replace("\\", "-")
            output.seek(0)
            file_path = os.path.join(base_dir, filename)
            with open(file_path, "wb") as f:
                f.write(output.getvalue())
            logger.info("Custom report saved at: %s", file_path)

        subject = f"Custom report for the project {project.name} - {dt}"
        message = (
            f"The custom report for the project {project.name} "
            "is ready and has been attached to this email."
        )

        if getattr(settings, "REPORTS_SEND_EMAILS", False):
            try:
                email = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user_email],
                )
                output.seek(0)
                if file_type == "xlsx":
                    email.attach(
                        f"custom_report_{dt}.xlsx",
                        output.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                else:
                    email.attach(
                        f"custom_report_{dt}.zip", output.getvalue(), "application/zip"
                    )
                email.send(fail_silently=False)
            except Exception as e:
                logger.exception("Error sending email report: %s", e)

        # Update to completed
        report_status.status = "completed"
        report_status.save()

    except Exception as e:
        # Update to failed
        report_status.status = "failed"
        report_status.error_message = str(e)
        report_status.save()
        raise


@app.task(name="process_pending_reports")
def process_pending_reports():
    """
    Periodic task to process pending reports, in chunks.
    """
    from chats.apps.api.v1.dashboard.presenter import ModelFieldsPresenter
    from chats.apps.api.v1.dashboard.viewsets import ReportFieldsValidatorViewSet

    # Select a pending report safely (avoid concurrency)
    with transaction.atomic():
        report = (
            ReportStatus.objects.select_for_update(skip_locked=True)
            .filter(status="pending")
            .order_by("created_on")
            .first()
        )
        if not report:
            logging.info("No pending reports to process.")
            return
        report.status = "processing"
        report.save()

    project = report.project
    fields_config = report.fields_config or {}
    user_email = report.user.email
    chunk_size = getattr(settings, "REPORTS_CHUNK_SIZE", 1)

    try:
        view = ReportFieldsValidatorViewSet()
        available_fields = ModelFieldsPresenter.get_models_info()

        # Decide formato
        file_type = _norm_file_type(fields_config.get("type"))
        output = io.BytesIO()

        if file_type == "xlsx":
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                # Sempre gerar apenas a aba 'rooms'
                rooms_cfg = (fields_config or {}).get("rooms") or {}
                query_data = None
                if rooms_cfg:
                    query_data = view._process_model_fields(
                        "rooms", rooms_cfg, project, available_fields
                    )

                def _write_queryset(sheet_name: str, qs):
                    total = qs.count()
                    row_offset = 0
                    for start in range(0, total, chunk_size):
                        end = min(start + chunk_size, total)
                        logging.info(
                            "Writing chunk: sheet=%s start=%s end=%s total=%s chunk_size=%s",
                            sheet_name,
                            start,
                            end,
                            total,
                            chunk_size,
                        )
                        chunk = list(qs[start:end])
                        chunk = _strip_tz(chunk)
                        if not chunk:
                            continue
                        df = pd.DataFrame(chunk)
                        df = _excel_safe_dataframe(df)
                        df.to_excel(
                            writer,
                            sheet_name=sheet_name[:31],
                            index=False,
                            header=(row_offset == 0),
                            startrow=row_offset if row_offset > 0 else 0,
                        )
                        row_offset += len(df)

                qs = (query_data or {}).get("queryset")
                if qs is not None:
                    if qs.count() > 0:
                        _write_queryset("rooms", qs)
                    else:
                        # Sem linhas: cria aba 'rooms' apenas com os headers escolhidos (se houver)
                        requested_fields = rooms_cfg.get("fields") or []
                        pd.DataFrame(columns=requested_fields).to_excel(
                            writer, sheet_name="rooms", index=False
                        )
                else:
                    # Nenhuma config de rooms: cria aba vazia para manter workbook válido
                    pd.DataFrame().to_excel(writer, sheet_name="rooms", index=False)
        else:
            # CSV: gera um zip com um CSV por aba
            csv_buffers = {}

            def _write_csv_queryset(sheet_name: str, qs):
                total = qs.count()
                row_offset = 0
                buf = csv_buffers.get(sheet_name)
                if buf is None:
                    buf = io.StringIO()
                    csv_buffers[sheet_name] = buf
                for start in range(0, total, chunk_size):
                    end = min(start + chunk_size, total)
                    logging.info(
                        "Writing chunk (csv): sheet=%s start=%s end=%s total=%s chunk_size=%s",
                        sheet_name,
                        start,
                        end,
                        total,
                        chunk_size,
                    )
                    chunk = list(qs[start:end])
                    chunk = _strip_tz(chunk)
                    if not chunk:
                        continue
                    df = pd.DataFrame(chunk)
                    df = _excel_safe_dataframe(df)
                    df.to_csv(buf, index=False, header=(row_offset == 0))
                    row_offset += len(df)

            if "rooms" in (fields_config or {}):
                query_data = view._process_model_fields(
                    "rooms", fields_config["rooms"], project, available_fields
                )
                if "queryset" in (query_data or {}):
                    _write_csv_queryset("rooms", query_data["queryset"])

            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for sheet_name, buf in csv_buffers.items():
                    zf.writestr(
                        f"{sheet_name[:31]}.csv", buf.getvalue().encode("utf-8")
                    )
            output = zip_buf

        dt = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        if getattr(settings, "REPORTS_SAVE_LOCALLY", True):
            base_dir = getattr(
                settings,
                "REPORTS_SAVE_DIR",
                os.path.join(settings.MEDIA_ROOT, "reports"),
            )
            os.makedirs(base_dir, exist_ok=True)
            ext = "xlsx" if file_type == "xlsx" else "zip"
            filename = f"custom_report_{project.uuid}_{dt}.{ext}"
            filename = filename.replace("/", "-").replace("\\", "-")
            output.seek(0)
            file_path = os.path.join(base_dir, filename)
            with open(file_path, "wb") as f:
                f.write(output.getvalue())
            logging.info(
                "Custom report saved at: %s | report_uuid=%s", file_path, report.uuid
            )
        logging.info(
            "Processing report %s for project %s done.", report.uuid, project.uuid
        )

        subject = f"Custom report for the project {project.name} - {dt}"
        message = (
            f"The custom report for the project {project.name} "
            "is ready and has been attached to this email."
        )

        if getattr(settings, "REPORTS_SEND_EMAILS", False):
            try:
                email = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user_email],
                )
                output.seek(0)
                if file_type == "xlsx":
                    email.attach(
                        f"custom_report_{dt}.xlsx",
                        output.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                else:
                    email.attach(
                        f"custom_report_{dt}.zip",
                        output.getvalue(),
                        "application/zip",
                    )
                email.send(fail_silently=False)
            except Exception as e:
                logging.exception("Error sending email report: %s", e)

        report.status = "completed"
        report.save()

    except Exception as e:
        logging.exception("Error processing pending report: %s", e)
        report.status = "failed"
        report.error_message = str(e)
        report.save()
