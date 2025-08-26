from uuid import UUID
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.dashboard.utils import calculate_response_time
from chats.apps.rooms.models import Room
from chats.celery import app
from chats.apps.projects.models import Project
from django.core.mail import EmailMessage
from django.conf import settings
import pandas as pd
from datetime import datetime, timezone
import io
import os
import logging
from chats.apps.dashboard.models import ReportStatus
from django.db import transaction
from typing import Optional

logger = logging.getLogger(__name__)


def _strip_tz_value(v):
    if isinstance(v, pd.Timestamp):
        try:
            if v.tz is not None:
                return v.tz_convert('UTC').tz_localize(None)
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
def generate_custom_fields_report(project_uuid: UUID, fields_config: dict, user_email: str, report_status_id: UUID):
    """
    Generate a custom report based on the fields configuration.
    """
    from chats.apps.api.v1.dashboard.viewsets import ReportFieldsValidatorViewSet
    
    project = Project.objects.get(uuid=project_uuid)
    report_generator = ReportFieldsValidatorViewSet()
    
    # Busca o objeto de status
    report_status = ReportStatus.objects.get(uuid=report_status_id)

    try:
        # Atualiza para processando
        report_status.status = 'processing'
        report_status.save()
        
        # Gera o relatório (código existente)
        report_data = report_generator._generate_report_data(fields_config, project)
        
        # Converte para DataFrame e depois para Excel
        output = io.BytesIO()
        
        # Cria um Excel writer
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Para cada modelo no relatório
            for model_name, model_data in report_data.items():
                # Converte os dados para DataFrame (removendo tz)
                df_data = _strip_tz(model_data.get('data', []))
                df = pd.DataFrame(df_data)
                df = _excel_safe_dataframe(df)
                if not df.empty:
                    df.to_excel(writer, sheet_name=model_name, index=False)
                
                # Processa dados relacionados
                related_data = model_data.get('related', {})
                for related_name, related_content in related_data.items():
                    sheet_name = f"{model_name}_{related_name}"
                    df_related_data = _strip_tz(related_content.get('data', []))
                    df_related = pd.DataFrame(df_related_data)
                    df_related = _excel_safe_dataframe(df_related)
                    if not df_related.empty:
                        df_related.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        
        # Salva arquivo localmente (timestamp sem barras)
        dt = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if getattr(settings, "REPORTS_SAVE_LOCALLY", True):
            base_dir = getattr(settings, "REPORTS_SAVE_DIR", os.path.join(settings.MEDIA_ROOT, "reports"))
            os.makedirs(base_dir, exist_ok=True)
            filename = f'custom_report_{project.uuid}_{dt}.xlsx'
            filename = filename.replace("/", "-").replace("\\", "-")
            output.seek(0)
            file_path = os.path.join(base_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(output.getvalue())
            logger.info("Custom report saved at: %s", file_path)
        else:
            logger.info("Local save disabled (REPORTS_SAVE_LOCALLY=False).")

        print("chegou aqui")
        # Prepara o email (opcional)
        subject = f"Relatório customizado do projeto {project.name} - {dt}"
        message = (
            f"O relatório customizado do projeto {project.name} "
            "está pronto e foi anexado a este email."
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
                email.attach(f'custom_report_{dt}.xlsx', output.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                email.send(fail_silently=False)
            except Exception as e:
                logger.exception("Erro ao enviar e-mail do relatório: %s", e)
        
        # Atualiza para concluído
        report_status.status = 'completed'
        report_status.save()
        
    except Exception as e:
        # Atualiza para falhou
        report_status.status = 'failed'
        report_status.error_message = str(e)
        report_status.save()
        raise


@app.task(name="process_pending_reports")
def process_pending_reports():
    """
    Tarefa periódica para processar relatórios pendentes, em chunks.
    """
    from chats.apps.api.v1.dashboard.viewsets import ReportFieldsValidatorViewSet
    from chats.apps.api.v1.dashboard.presenter import ModelFieldsPresenter

    # Seleciona um relatório pendente de forma segura (evita concorrência)
    with transaction.atomic():
        report = (
            ReportStatus.objects.select_for_update(skip_locked=True)
            .filter(status='pending')
            .order_by('created_on')
            .first()
        )
        if not report:
            logging.info("No pending reports to process.")
            return
        report.status = 'processing'
        report.save()

    project = report.project
    fields_config = report.fields_config or {}
    user_email = report.user.email
    chunk_size = getattr(settings, "REPORTS_CHUNK_SIZE", 1)

    try:
        view = ReportFieldsValidatorViewSet()
        available_fields = ModelFieldsPresenter.get_models_info()

        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            wrote_any = False
            for model_name, field_data in fields_config.items():
                query_data = view._process_model_fields(
                    model_name, field_data, project, available_fields
                )

                def _write_queryset(sheet_name: str, qs):
                    total = qs.count()
                    row_offset = 0
                    for start in range(0, total, chunk_size):
                        end = min(start + chunk_size, total)
                        logging.info("Writing chunk: sheet=%s start=%s end=%s total=%s chunk_size=%s",
                                     sheet_name, start, end, total, chunk_size)
                        chunk = list(qs[start:end])
                        # Remove timezone de todos os valores antes de montar o DataFrame
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
                        wrote_any = True

                if 'queryset' in query_data:
                    _write_queryset(model_name, query_data['queryset'])

                for related_name, related_qd in (query_data.get('related') or {}).items():
                    if 'queryset' in related_qd:
                        _write_queryset(f"{model_name}_{related_name}", related_qd['queryset'])

            if not wrote_any:
                # Cria ao menos uma aba para workbook válido
                meta = pd.DataFrame([{"message": "No data for the selected configuration"}])
                meta.to_excel(writer, sheet_name='metadata', index=False)

        dt = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Salva arquivo localmente
        if getattr(settings, "REPORTS_SAVE_LOCALLY", True):
            base_dir = getattr(settings, "REPORTS_SAVE_DIR", os.path.join(settings.MEDIA_ROOT, "reports"))
            os.makedirs(base_dir, exist_ok=True)
            filename = f'custom_report_{project.uuid}_{dt}.xlsx'
            filename = filename.replace("/", "-").replace("\\", "-")
            output.seek(0)
            file_path = os.path.join(base_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(output.getvalue())
            logging.info("Custom report saved at: %s | report_uuid=%s", file_path, report.uuid)
        else:
            logging.info("Local save disabled (REPORTS_SAVE_LOCALLY=False).")
        logging.info("Processing report %s for project %s done.", report.uuid, project.uuid)

        subject = f"Relatório customizado do projeto {project.name} - {dt}"
        message = (
            f"O relatório customizado do projeto {project.name} "
            "está pronto e foi anexado a este email."
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
                email.attach(
                    f'custom_report_{dt}.xlsx',
                    output.getvalue(),
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
                email.send(fail_silently=False)
            except Exception as e:
                logging.exception("Erro ao enviar e-mail do relatório: %s", e)

        report.status = 'completed'
        report.save()

    except Exception as e:
        logging.exception("Erro ao processar relatório pendente: %s", e)
        report.status = 'failed'
        report.error_message = str(e)
        report.save()
