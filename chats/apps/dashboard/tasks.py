from uuid import UUID
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.dashboard.utils import calculate_response_time
from chats.apps.rooms.models import Room
from chats.celery import app
from chats.apps.projects.models import Project
from django.core.mail import EmailMessage
from django.conf import settings
import pandas as pd
from datetime import datetime
import io
import logging
from chats.apps.dashboard.models import ReportStatus
from django.db import transaction

logger = logging.getLogger(__name__)


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
                # Converte os dados para DataFrame
                df = pd.DataFrame(model_data.get('data', []))
                if not df.empty:
                    df.to_excel(writer, sheet_name=model_name, index=False)
                
                # Processa dados relacionados
                related_data = model_data.get('related', {})
                for related_name, related_content in related_data.items():
                    sheet_name = f"{model_name}_{related_name}"
                    df_related = pd.DataFrame(related_content.get('data', []))
                    if not df_related.empty:
                        df_related.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        
        # Prepara o email
        dt = datetime.now().strftime("%d/%m/%Y_%H-%M-%S")
        subject = f"Relatório customizado do projeto {project.name} - {dt}"
        message = (
            f"O relatório customizado do projeto {project.name} "
            "está pronto e foi anexado a este email."
        )

        if settings.SEND_EMAILS:
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email],
            )
            
            # Anexa o Excel
            output.seek(0)
            email.attach(f'custom_report_{dt}.xlsx', output.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            email.send(fail_silently=False)
        
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
            return
        report.status = 'processing'
        report.save()

    project = report.project
    fields_config = report.fields_config or {}
    user_email = report.user.email
    chunk_size = getattr(settings, "REPORTS_CHUNK_SIZE", 5000)

    try:
        view = ReportFieldsValidatorViewSet()
        available_fields = ModelFieldsPresenter.get_models_info()

        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for model_name, field_data in fields_config.items():
                query_data = view._process_model_fields(
                    model_name, field_data, project, available_fields
                )

                def _write_queryset(sheet_name: str, qs):
                    total = qs.count()
                    row_offset = 0
                    for start in range(0, total, chunk_size):
                        end = min(start + chunk_size, total)
                        chunk = list(qs[start:end])
                        if not chunk:
                            continue
                        df = pd.DataFrame(chunk)
                        df.to_excel(
                            writer,
                            sheet_name=sheet_name[:31],
                            index=False,
                            header=(row_offset == 0),
                            startrow=row_offset if row_offset > 0 else 0,
                        )
                        row_offset += len(df)

                if 'queryset' in query_data:
                    _write_queryset(model_name, query_data['queryset'])

                for related_name, related_qd in (query_data.get('related') or {}).items():
                    if 'queryset' in related_qd:
                        _write_queryset(f"{model_name}_{related_name}", related_qd['queryset'])

        dt = datetime.now().strftime("%d/%m/%Y_%H-%M-%S")
        subject = f"Relatório customizado do projeto {project.name} - {dt}"
        message = (
            f"O relatório customizado do projeto {project.name} "
            "está pronto e foi anexado a este email."
        )

        if settings.SEND_EMAILS:
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

        report.status = 'completed'
        report.save()

    except Exception as e:
        logging.exception("Erro ao processar relatório pendente: %s", e)
        report.status = 'failed'
        report.error_message = str(e)
        report.save()
