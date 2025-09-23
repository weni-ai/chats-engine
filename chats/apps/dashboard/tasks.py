import io
import logging
import os
import zipfile
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

import pandas as pd
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.core.files.base import ContentFile

from chats.apps.dashboard.models import ReportStatus, RoomMetrics
from chats.apps.dashboard.utils import (
    calculate_last_queue_waiting_time,
    calculate_response_time,
)
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room
from chats.celery import app
from chats.core.excel_storage import ExcelStorage

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
    metric_room.save()


@app.task(name="close_metrics")
def close_metrics(room_uuid: UUID):
    """
    Close metrics for a room.
    """
    generate_metrics(room_uuid)


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
        # Update to in_progress
        report_status.status = "in_progress"
        report_status.save()

        # Generate the report: filter only known models and ignore auxiliary keys (ex.: 'type')
        from chats.apps.api.v1.dashboard.presenter import ModelFieldsPresenter

        available_fields = ModelFieldsPresenter.get_models_info()
        models_config = {
            k: v for k, v in (fields_config or {}).items() if k in available_fields
        }
        report_data = report_generator._generate_report_data(models_config, project)

        # Generate in XLSX (default) or CSV
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
            csv_buf = io.BytesIO()
            df_data = _strip_tz(report_data.get("rooms", {}).get("data", []))
            df = pd.DataFrame(df_data)
            df = _excel_safe_dataframe(df)
            csv_buf.write(df.to_csv(index=False).encode("utf-8"))
            output = csv_buf

        dt = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        if getattr(settings, "REPORTS_SAVE_LOCALLY", True):
            base_dir = getattr(
                settings,
                "REPORTS_SAVE_DIR",
                os.path.join(settings.MEDIA_ROOT, "reports"),
            )
            os.makedirs(base_dir, exist_ok=True)
            ext = "xlsx" if file_type == "xlsx" else "csv"
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
                        f"custom_report_{dt}.csv", output.getvalue(), "text/csv"
                    )
                email.send(fail_silently=False)
            except Exception as e:
                logger.exception("Error sending email report: %s", e)

        # Update to ready
        report_status.status = "ready"
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
        # Também reprocessa relatórios 'failed' e 'processing' estagnados
        stale_seconds = getattr(settings, "REPORTS_STALE_SECONDS", None)
        if stale_seconds is not None:
            stale_after = datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)
        else:
            stale_after = datetime.now(timezone.utc) - timedelta(
                minutes=getattr(settings, "REPORTS_STALE_MINUTES", 10)
            )
        report = (
            ReportStatus.objects.select_for_update(skip_locked=True)
            .filter(
                Q(status__in=["pending", "failed"])
                | Q(status="in_progress", modified_on__lt=stale_after)  # Corrigir aqui
            )
            .order_by("created_on")
            .first()
        )
        if not report:
            logging.info("No pending reports to process.")
            return
        report.status = "in_progress"
        report.save()

    project = report.project
    fields_config = report.fields_config or {}
    user_email = report.user.email
    chunk_size = getattr(settings, "REPORTS_CHUNK_SIZE", 1)

    try:
        view = ReportFieldsValidatorViewSet()
        available_fields = ModelFieldsPresenter.get_models_info()

        # Formato final (xlsx ou csv)
        file_type = _norm_file_type(fields_config.get("type"))
        storage = ExcelStorage()
        dt = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        parts_dir = f"reports/{project.uuid}/{report.uuid}/tmp"

        # rooms queryset (única aba suportada)
        rooms_cfg = (fields_config or {}).get("rooms") or {}
        query_data = None
        if rooms_cfg:
            query_data = view._process_model_fields(
                "rooms", rooms_cfg, project, available_fields
            )
        qs = (query_data or {}).get("queryset")

        # Listar partes já existentes para retomar
        def _list_existing_parts():
            try:
                # retorna (subdirs, files) relativos a parts_dir
                subdirs, files = storage.listdir(parts_dir)
            except Exception:
                subdirs, files = [], []
            files = sorted(
                [f for f in files if f.startswith("rooms.part") and f.endswith(".csv")]
            )
            # reconstruir caminhos completos
            return [f"{parts_dir}/{name}" for name in files]

        existing_parts = _list_existing_parts()
        existing_count = len(existing_parts)

        # Conta exatamente quantas linhas já persistimos nas partes
        def _count_processed_rows() -> int:
            total_rows = 0
            first = True
            for p in existing_parts:
                try:
                    with storage.open(p, "rb") as f:
                        content = f.read().decode("utf-8")
                except Exception:
                    first = False
                    continue
                if not content:
                    first = False
                    continue
                lines = [ln for ln in content.splitlines() if ln.strip()]
                if not lines:
                    first = False
                    continue
                if first:
                    # primeira parte inclui header
                    total_rows += max(0, len(lines) - 1)
                else:
                    total_rows += len(lines)
                first = False
            return total_rows

        next_start = _count_processed_rows()
        logging.info(
            "Resuming report: parts=%s, processed_rows=%s, chunk_size=%s",
            existing_count,
            next_start,
            chunk_size,
        )

        # Função para escrever partes de CSV (header só na primeira parte)
        def _write_parts_from_queryset(qs):
            total = qs.count()
            if total == 0:
                return
            part_idx = existing_count
            header_written = existing_count > 0
            for start in range(next_start, total, chunk_size):
                end = min(start + chunk_size, total)
                # Heartbeat: atualiza modified_on para não ser considerado 'stale'
                try:
                    report.save(update_fields=["modified_on"])
                except Exception:
                    pass
                logging.info(
                    "Writing chunk (part): sheet=%s start=%s end=%s total=%s chunk_size=%s",
                    "rooms",
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
                csv_str = df.to_csv(index=False, header=(not header_written))
                part_name = f"{parts_dir}/rooms.part{part_idx:06d}.csv"
                storage.save(part_name, ContentFile(csv_str.encode("utf-8")))
                header_written = True
                part_idx += 1

        # Geração de partes (se houver queryset)
        if qs is not None:
            _write_parts_from_queryset(qs)

        # Finalização: montar arquivo final a partir das partes
        def _finalize_from_parts() -> bytes:
            parts = _list_existing_parts()
            if file_type == "xlsx":
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                    current_row = 0
                    if not parts:
                        # somente headers (se fornecidos)
                        requested_fields = rooms_cfg.get("fields") or []
                        pd.DataFrame(columns=requested_fields).to_excel(
                            writer, sheet_name="rooms", index=False
                        )
                    else:
                        first = True
                        for p in parts:
                            with storage.open(p, "rb") as f:
                                content = f.read().decode("utf-8")
                            if not content:
                                continue
                            if not first and "\n" in content:
                                content = content.split("\n", 1)[1]
                            if not content.strip():
                                first = False
                                continue
                            df = pd.read_csv(io.StringIO(content))
                            if df.empty:
                                first = False
                                continue
                            df.to_excel(
                                writer,
                                sheet_name="rooms",
                                index=False,
                                header=(current_row == 0),
                                startrow=current_row if current_row > 0 else 0,
                            )
                            current_row += len(df)
                            first = False
                out.seek(0)
                return out.getvalue()
            else:
                # CSV puro (concatena partes, preserva header da primeira)
                combined = io.StringIO()
                if not parts:
                    requested_fields = rooms_cfg.get("fields") or []
                    if requested_fields:
                        combined.write(",".join(requested_fields) + "\n")
                else:
                    first = True
                    for p in parts:
                        with storage.open(p, "rb") as f:
                            content = f.read().decode("utf-8")
                        if not content:
                            continue
                        if first:
                            combined.write(content)
                            first = False
                        else:
                            content = content.split("\n", 1)[1] if "\n" in content else ""
                            combined.write(content)
                return combined.getvalue().encode("utf-8")

        final_bytes = _finalize_from_parts()
        output = io.BytesIO(final_bytes)

        if getattr(settings, "REPORTS_SAVE_LOCALLY", True):
            base_dir = getattr(
                settings,
                "REPORTS_SAVE_DIR",
                os.path.join(settings.MEDIA_ROOT, "reports"),
            )
            os.makedirs(base_dir, exist_ok=True)
            ext = "xlsx" if file_type == "xlsx" else "csv"
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
                        f"custom_report_{dt}.csv",
                        output.getvalue(),
                        "text/csv",
                    )
                email.send(fail_silently=False)
            except Exception as e:
                logging.exception("Error sending email report: %s", e)

        report.status = "ready"
        report.save()

    except Exception as e:
        logging.exception("Error processing pending report: %s", e)
        report.status = "failed"
        report.error_message = str(e)
        report.save()
