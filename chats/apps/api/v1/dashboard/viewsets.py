import io
import json

import pandas
from django.http import HttpResponse
from chats.apps.dashboard.tasks import generate_custom_fields_report
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import NotFound

from chats.apps.api.v1.dashboard.presenter import get_export_data
from chats.apps.api.v1.dashboard.repository import (
    ORMRoomsDataRepository,
    RoomsCacheRepository,
)
from chats.apps.api.v1.dashboard.serializers import (
    DashboardAgentsSerializer,
    DashboardRawDataSerializer,
    DashboardRoomSerializer,
    DashboardSectorSerializer,
)
from chats.apps.api.v1.permissions import IsProjectAdminSpecific, IsProjectAdmin
from chats.apps.projects.models import Project, ProjectPermission
from chats.core.excel_storage import ExcelStorage

from .dto import Filters, should_exclude_admin_domains
from .service import AgentsService, RawDataService, RoomsDataService, SectorService
from .presenter import ModelFieldsPresenter
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.apps import apps
from django.db.models import Q
from chats.celery import app
from django.core.mail import EmailMessage
from django.conf import settings
import logging
from uuid import UUID
from chats.apps.dashboard.models import ReportStatus
import pendulum

logger = logging.getLogger(__name__)


class DashboardLiveViewset(viewsets.GenericViewSet):
    lookup_field = "uuid"
    queryset = Project.objects.all()

    @action(
        detail=True,
        methods=["GET"],
        url_name="general",
    )
    def general(self, request, *args, **kwargs):
        """General metrics for the project or the sector"""
        project = self.get_object()

        user_permission = ProjectPermission.objects.select_related(
            "user", "project"
        ).get(user=request.user, project=project)
        params = request.query_params.dict()
        filters = Filters(
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            agent=params.get("agent"),
            sector=params.get("sector"),
            tag=params.get("tag"),
            queue=params.get("queue"),
            user_request=user_permission,
            project=project,
            is_weni_admin=should_exclude_admin_domains(
                request.user.email if request.user else ""
            ),
        )

        rooms_service = RoomsDataService(
            ORMRoomsDataRepository(), RoomsCacheRepository()
        )
        rooms_data = rooms_service.get_rooms_data(filters)

        return Response({"rooms_data": rooms_data}, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        url_name="agent",
    )
    def agent(self, request, *args, **kwargs):
        """Agent metrics for the project or the sector"""
        project = self.get_object()
        params = request.query_params.dict()
        filters = Filters(
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            agent=params.get("agent"),
            sector=params.get("sector"),
            tag=params.get("tag"),
            queue=params.get("queue"),
            user_request=request.user,
            is_weni_admin=should_exclude_admin_domains(
                request.user.email if request.user else ""
            ),
        )

        agents_service = AgentsService()
        agents_data = agents_service.get_agents_data(filters, project)
        agents = DashboardAgentsSerializer(agents_data, many=True)

        return Response({"project_agents": agents.data}, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        url_name="division",
    )
    def division(self, request, *args, **kwargs):
        """
        Can return data on project and sector level (list of sector or list of queues)
        """
        project = self.get_object()
        params = request.query_params.dict()

        user_permission = ProjectPermission.objects.select_related(
            "user", "project"
        ).get(user=request.user, project=project)
        filters = Filters(
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            agent=params.get("agent"),
            sector=params.get("sector"),
            queue=params.get("queue"),
            tag=params.get("tag"),
            user_request=user_permission,
            project=project,
            is_weni_admin=should_exclude_admin_domains(
                request.user.email if request.user else ""
            ),
        )

        sectors_service = SectorService()
        sectors_data = sectors_service.get_sector_data(filters)
        serialized_data = DashboardSectorSerializer(sectors_data, many=True)
        return Response({"sectors": serialized_data.data}, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        url_name="raw",
        serializer_class=DashboardRawDataSerializer,
    )
    def raw_data(self, request, *args, **kwargs):
        """Raw data for the project, sector, queue and agent."""
        project = self.get_object()
        params = request.query_params.dict()
        user_permission = ProjectPermission.objects.select_related(
            "user", "project"
        ).get(user=request.user, project=project)
        filters = Filters(
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            agent=params.get("agent"),
            sector=params.get("sector"),
            queue=params.get("queue"),
            tag=params.get("tag"),
            user_request=user_permission,
            project=project,
            is_weni_admin=should_exclude_admin_domains(
                request.user.email if request.user else ""
            ),
        )

        raw_service = RawDataService()
        raw_data_count = raw_service.get_raw_data(filters)

        return Response(raw_data_count, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        url_name="export",
    )
    def export(self, request, *args, **kwargs):
        """
        Can return data to be export in csv on project and sector level (list of sector or list of queues)
        """
        project = self.get_object()
        filter = request.query_params
        dataset = get_export_data(project, filter)
        data_frame_rooms = pandas.DataFrame(dataset)

        filename = "dashboard_rooms_export_data"

        if "xls" in filter:
            excel_rooms_buffer = io.BytesIO()
            with pandas.ExcelWriter(excel_rooms_buffer, engine="xlsxwriter") as writer:
                data_frame_rooms.to_excel(
                    writer,
                    sheet_name="rooms_infos",
                    startrow=1,
                    startcol=0,
                    index=False,
                )
            excel_rooms_buffer.seek(0)
            storage = ExcelStorage()

            bytes_archive = excel_rooms_buffer.getvalue()

            with storage.open(filename + ".xlsx", "wb") as up_file:
                up_file.write(bytes_archive)
                file_url = storage.url(up_file.name)

            data = {"path_file": file_url}

            return HttpResponse(
                json.dumps(data),
                content_type="application/javascript; charset=utf8",
            )
        else:
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="' + filename + ".csv"
            )

            table = pandas.DataFrame(dataset)
            if not table.empty:
                table.rename(
                    columns={
                        0: "Nome da Fila",
                        1: "Tempo de espera",
                        2: "Tempo de resposta",
                        3: "Tempo de interação",
                        4: "Aberta",
                    },
                    inplace=True,
                )
            table.to_csv(response, encoding="utf-8", index=False)
            return response

    @action(
        detail=True,
        methods=["GET"],
        url_name="export_dashboard",
    )
    def export_dashboard(self, request, *args, **kwargs):
        """
        Can return data from dashboard to be export in csv/xls on project
        and sector level (list of sector, list of queues and list of agents online)
        """
        project = self.get_object()
        filter = request.query_params
        user_permission = ProjectPermission.objects.select_related(
            "user", "project"
        ).get(user=request.user, project=project)
        filters = Filters(
            start_date=filter.get("start_date"),
            end_date=filter.get("end_date"),
            agent=filter.get("agent"),
            sector=filter.get("sector"),
            queue=filter.get("queue"),
            tag=filter.get("tag"),
            user_request=user_permission,
            project=project,
            is_weni_admin=should_exclude_admin_domains(
                request.user.email if request.user else ""
            ),
        )

        # Rooms Data
        rooms_service = RoomsDataService(
            ORMRoomsDataRepository(), RoomsCacheRepository()
        )
        rooms_data = rooms_service.get_rooms_data(filters)
        rooms_serializer = DashboardRoomSerializer(rooms_data, many=True)
        data_frame = pandas.DataFrame(rooms_serializer.data)
        if not data_frame.empty:
            data_frame.columns = [
                "Tempo de Espera",
                "Tempo de Resposta",
                "Tempo de Interação",
            ]

        # Raw Data
        raw_data_service = RawDataService()
        raw_data = raw_data_service.get_raw_data(filters)
        raw_data_serializer = DashboardRawDataSerializer(
            raw_data["raw_data"], many=True
        )
        data_frame_1 = pandas.DataFrame(raw_data_serializer.data)
        if not data_frame_1.empty:
            data_frame_1.columns = [
                "Salas Ativas",
                "Salas Fechadas",
                "Transferencias",
                "Salas na Fila",
            ]
        # Sector Data
        sector_data_service = SectorService()
        sector_data = sector_data_service.get_sector_data(filters)
        sector_dataset = DashboardSectorSerializer(sector_data, many=True)
        data_frame_2 = pandas.DataFrame(sector_dataset.data)
        data_frame_2 = data_frame_2[
            ["name", "waiting_time", "response_time", "interact_time"]
        ]

        if not data_frame_2.empty:
            data_frame_2.columns = [
                "Nome",
                "Tempo de Espera",
                "Tempo de Resposta",
                "Tempo de Interação",
            ]

        # Agents Data
        agents_service = AgentsService()
        agents_data = agents_service.get_agents_data(filters, project)
        agents_dataset = DashboardAgentsSerializer(agents_data, many=True)
        data_frame_3 = pandas.DataFrame(agents_dataset.data)
        if not data_frame_3.empty:
            data_frame_3.columns = [
                "Nome",
                "Sobrenome",
                "Email",
                "Status",
                "Salas Fechadas",
                "Salas Abertas",
            ]

        filename = "dashboard_export_data"
        if "xls" in filter:
            excel_buffer = io.BytesIO()
            with pandas.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                data_frame.to_excel(
                    writer,
                    sheet_name="dashboard_infos",
                    startrow=0,
                    startcol=0,
                    index=False,
                )

                start_row_1 = len(data_frame.index) + 2
                data_frame_1.to_excel(
                    writer,
                    sheet_name="dashboard_infos",
                    startrow=start_row_1,
                    startcol=0,
                    index=False,
                )

                start_row_2 = start_row_1 + len(data_frame_1.index) + 2
                data_frame_2.to_excel(
                    writer,
                    sheet_name="dashboard_infos",
                    startrow=start_row_2,
                    startcol=0,
                    index=False,
                )

                start_row_3 = start_row_2 + len(data_frame_2.index) + 2
                data_frame_3.to_excel(
                    writer,
                    sheet_name="dashboard_infos",
                    startrow=start_row_3,
                    startcol=0,
                    index=False,
                )

            excel_buffer.seek(0)
            storage = ExcelStorage()

            bytes_archive = excel_buffer.getvalue()

            with storage.open(filename + ".xlsx", "wb") as up_file:
                up_file.write(bytes_archive)
                file_url = storage.url(up_file.name)

            data = {"path_file": file_url}

            return HttpResponse(
                json.dumps(data),
                content_type="application/javascript; charset=utf8",
            )

        else:
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="' + filename + ".csv"
            )

            data_frame.to_csv(response, index=False, mode="a", sep=";"),
            response.write("\n")
            data_frame_1.to_csv(response, index=False, mode="a", sep=";")
            response.write("\n")
            data_frame_2.to_csv(response, index=False, mode="a", sep=";")
            response.write("\n")
            data_frame_3.to_csv(response, index=False, mode="a", sep=";")

            return response

    @action(detail=True, methods=['get'])
    def report_status(self, request, **kwargs):
        """Verifica o status de um relatório"""
        try:
            # Pega o UUID tanto de 'pk' quanto de 'uuid'
            report_uuid = kwargs.get('uuid') or kwargs.get('pk')
            
            # Para teste - remove o filtro de user
            report_status = ReportStatus.objects.get(uuid=report_uuid)
            return Response({
                'status': report_status.status,
                'error_message': report_status.error_message
            })
        except ReportStatus.DoesNotExist:
            return Response({'error': 'Report not found'}, status=404)


class ModelFieldsViewSet(viewsets.GenericViewSet):
    """
    Endpoint para retornar os campos disponíveis dos principais models do sistema.
    """
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(ModelFieldsPresenter.get_models_info())


class ReportFieldsValidatorViewSet(viewsets.GenericViewSet):
    """
    Endpoint para validar campos e gerar consulta para relatório baseado nos campos disponíveis.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_model_class(self, model_name):
        """
        Encontra a classe do modelo Django baseado no nome
        """
        # Mapeamento dos modelos conhecidos
        model_mapping = {
            'sectors': ('sectors', 'Sector'),
            'queues': ('queues', 'Queue'),
            'rooms': ('rooms', 'Room'),
            'users': ('accounts', 'User'),
            'sector_tags': ('sectors', 'SectorTag'),
            'contacts': ('contacts', 'Contact')
        }
        
        if model_name in model_mapping:
            app_label, model_class_name = model_mapping[model_name]
            try:
                return apps.get_model(app_label=app_label, model_name=model_class_name)
            except LookupError:
                pass
        
        # Fallback: busca nos apps comuns
        common_apps = ['sectors', 'queues', 'rooms', 'accounts', 'contacts', 'msgs', 'projects']
        for app in common_apps:
            try:
                return apps.get_model(app_label=app, model_name=model_name.capitalize())
            except LookupError:
                continue
        
        return None

    def _get_model_count_for_project(self, model_class, project):
        """
        Conta registros de um modelo específico para um projeto
        """
        try:
            model_fields = {field.name: field for field in model_class._meta.get_fields()}
            
            filters = Q()
            
            # Aplica filtros baseados nos campos disponíveis
            if 'project' in model_fields:
                filters |= Q(project=project)
            if 'sector' in model_fields:
                filters |= Q(sector__project=project)
            if 'queue' in model_fields:
                filters |= Q(queue__sector__project=project)
            if 'user' in model_fields:
                filters |= Q(user__project_permissions__project=project)
            
            if filters:
                return model_class.objects.filter(filters).distinct().count()
            else:
                # Se não conseguiu filtrar por projeto, retorna uma estimativa conservadora
                total_count = model_class.objects.count()
                return max(1, total_count // 10)  # 10% do total
                
        except Exception as e:
            logger.error(f"Erro ao contar registros para {model_class.__name__}: {e}")
            return 0

    def _estimate_execution_time(self, fields_config, project):
        """
        Estima o tempo de execução baseado no volume de dados que será processado
        """
        # Verifica se os modelos são válidos
        available_models = ModelFieldsPresenter.get_models_info()
        invalid_models = [model for model in fields_config.keys() 
                         if model not in available_models]
        
        if invalid_models:
            raise ValidationError(
                f"Models not available: {', '.join(invalid_models)}. "
                f"Models available: {', '.join(sorted(available_models.keys()))}"
            )
        
        total_records = 0
        processed_models = []
        
        # Conta registros que serão processados
        for model_name in fields_config.keys():
            try:
                model_class = self._get_model_class(model_name)
                
                if model_class:
                    count = self._get_model_count_for_project(model_class, project)
                    total_records += count
                    processed_models.append({
                        'model': model_name,
                        'count': count
                    })
                    logger.info(f"Modelo {model_name}: {count} registros")
                else:
                    logger.warning(f"Modelo {model_name} não encontrado")
                    
            except Exception as e:
                logger.error(f"Erro ao processar modelo {model_name}: {e}")
                continue
        
        # Estimativas baseadas em testes empíricos
        base_time = 30  # segundos base
        time_per_1000_records = 45  # segundos por 1000 registros
        
        # Fator de complexidade baseado no número de modelos
        complexity_factor = 1 + (len(processed_models) * 0.1)
        
        # Calcula estimativa
        if total_records > 0:
            estimated_time = (base_time + (total_records / 1000) * time_per_1000_records) * complexity_factor
        else:
            estimated_time = base_time
        
        # Limita a estimativa (mínimo 30s, máximo 10min)
        final_estimate = max(30, min(int(estimated_time), 600))
        
        logger.info(f"Estimativa de tempo: {final_estimate}s para {total_records} registros em {len(processed_models)} modelos")
        
        return final_estimate

    def _get_base_queryset(self, model_name, project):
        """
        Retorna o queryset base para qualquer modelo retornado pelo ModelFieldsPresenter
        """
        available_fields = ModelFieldsPresenter.get_models_info()
        
        if model_name not in available_fields:
            raise NotFound(f'Model "{model_name}" not found')
            
        # Usa o método _get_model_class que já existe e tem o mapeamento correto
        model = self._get_model_class(model_name)
        
        if model is None:
            raise NotFound(f'Model "{model_name}" not found')

        # Constrói a query base COM FILTRO DE PROJETO
        queryset = model.objects.all()
        
        # Aplica filtro específico para cada modelo
        if model_name == 'sectors':
            queryset = queryset.filter(project=project)
        elif model_name == 'queues':
            queryset = queryset.filter(sector__project=project)
        elif model_name == 'rooms':
            queryset = queryset.filter(queue__sector__project=project)
        elif model_name == 'contacts':
            queryset = queryset.filter(rooms__queue__sector__project=project).distinct()
        elif model_name == 'users':
            queryset = queryset.filter(project_permissions__project=project).distinct()
        elif model_name == 'sector_tags':
            queryset = queryset.filter(sector__project=project)
        
        return queryset

    def _process_model_fields(self, model_name, field_data, project, available_fields):
        """
        Processa os campos de um modelo e suas relações
        """
        if model_name not in available_fields:
            raise NotFound(f'Model "{model_name}" not found')

        model_fields = available_fields[model_name]
        query_fields = []
        related_queries = {}

        for key, value in field_data.items():
            if key == 'fields' and isinstance(value, list):
                # Permite campos diretos E lookups (campo__subcampo)
                invalid_fields = []
                for field in value:
                    # Aceita campos diretos
                    if field in model_fields:
                        continue
                    # Aceita lookups simples
                    if '__' in field:
                        base_field = field.split('__')[0]
                        if base_field in model_fields:
                            continue
                    # Campo inválido
                    invalid_fields.append(field)

                if invalid_fields:
                    raise NotFound(f'Campos inválidos para {model_name}: {", ".join(invalid_fields)}')
                query_fields.extend(value)
            elif key in available_fields:
                # Processa campos relacionados
                related_queries[key] = self._process_model_fields(key, value, project, available_fields)

        # Obtém o queryset base (JÁ FILTRADO POR PROJETO)
        base_queryset = self._get_base_queryset(model_name, project)

        # [NOVO] Filtro por lista de uuids (genérico por modelo)
        uuids = field_data.get('uuids')
        if isinstance(uuids, list) and uuids:
            # "__all__" => não aplica filtro
            if "__all__" not in uuids:
                base_queryset = base_queryset.filter(uuid__in=uuids)

        # [NOVO] Filtros específicos de rooms: open_chats/closed_chats
        if model_name == 'rooms':
            open_chats = field_data.get('open_chats')
            closed_chats = field_data.get('closed_chats')
            if open_chats is True and closed_chats is True:
                raise ValidationError('open_chats and closed_chats cannot be used together.')
            if open_chats is True:
                base_queryset = base_queryset.filter(is_active=True)
            if closed_chats is True:
                base_queryset = base_queryset.filter(is_active=False)

        # Aplica o filtro de datas nas queries de rooms
        if model_name == 'rooms':
            start_date = field_data.get('start_date')
            end_date = field_data.get('end_date')
            if start_date and end_date:
                tz = project.timezone
                start_dt = pendulum.parse(start_date).replace(tzinfo=tz)
                end_dt = pendulum.parse(end_date + " 23:59:59").replace(tzinfo=tz)
                base_queryset = base_queryset.filter(created_on__range=[start_dt, end_dt])

        # Aplica os campos selecionados
        if query_fields:
            base_queryset = base_queryset.values(*query_fields)

        # NÃO aplica filtros genéricos com OR - o filtro já foi aplicado em _get_base_queryset

        return {
            'queryset': base_queryset,
            'related': related_queries
        }

    def _group_duplicate_records(self, raw_data):
        """
        Agrupa registros duplicados causados por lookups de relações Many-to-Many ou ForeignKey reverso
        """
        if not raw_data:
            return []
        
        # Identifica campos de agrupamento (campos sem __)
        sample_row = raw_data[0]
        group_fields = [key for key in sample_row.keys() if '__' not in key]
        lookup_fields = [key for key in sample_row.keys() if '__' in key]
        
        # Se não há campos de agrupamento ou lookups, retorna os dados originais
        if not group_fields or not lookup_fields:
            return raw_data
        
        # Agrupa os registros
        grouped_data = {}
        
        for row in raw_data:
            # Cria chave de agrupamento baseada nos campos diretos
            group_key = tuple(row.get(field) for field in group_fields)
            
            if group_key not in grouped_data:
                # Primeiro registro do grupo - inicializa com campos diretos
                grouped_data[group_key] = {field: row.get(field) for field in group_fields}
                # Inicializa listas para campos com lookup
                for field in lookup_fields:
                    grouped_data[group_key][field] = []
            
            # Adiciona valores dos campos com lookup às listas
            for field in lookup_fields:
                value = row.get(field)
                if value is not None and value not in grouped_data[group_key][field]:
                    grouped_data[group_key][field].append(value)
        
        # Converte de volta para lista de dicionários
        result = list(grouped_data.values())
        
        # Para campos com apenas um valor na lista, desempacota
        for row in result:
            for field in lookup_fields:
                if len(row[field]) == 1:
                    row[field] = row[field][0]
                elif len(row[field]) == 0:
                    row[field] = None
        
        return result

    def _execute_queries(self, query_data):
        """
        Executa as queries e formata o resultado
        """
        result = {}
        
        if 'queryset' in query_data:
            try:
                # Executa a query
                raw_data = list(query_data['queryset'])
                
                # Detecta se há campos com lookups que podem causar duplicação
                has_lookups = any('__' in str(key) for row in raw_data[:1] for key in row.keys()) if raw_data else False
                
                if has_lookups and raw_data:
                    # Agrupa registros duplicados causados por lookups
                    result['data'] = self._group_duplicate_records(raw_data)
                else:
                    result['data'] = raw_data
                    
            except Exception as e:
                raise ValidationError(f'Error executing query: {str(e)}')

        if 'related' in query_data:
            for model, related_data in query_data['related'].items():
                result[model] = self._execute_queries(related_data)

        return result

    def _generate_report_data(self, data, project):
        """
        Método interno para gerar os dados do relatório
        """
        available_fields = ModelFieldsPresenter.get_models_info()
        
        # Processa cada modelo e seus campos
        queries = {}
        for model_name, field_data in data.items():
            queries[model_name] = self._process_model_fields(
                model_name,
                field_data,
                project,
                available_fields
            )
        
        # Executa as queries e formata o resultado
        report_data = {}
        for model_name, query_data in queries.items():
            report_data[model_name] = self._execute_queries(query_data)
            
        return report_data

    def create(self, request):
        project_uuid = request.data.get('project_uuid')
        if not project_uuid:
            raise ValidationError({'project_uuid': 'This field is required.'})
        
        project = get_object_or_404(Project, uuid=project_uuid)
        
        try:
            # Remove project_uuid do processamento
            fields_config = {k: v for k, v in request.data.items() 
                        if k != 'project_uuid'}

            # [NOVO] Extrai flags de nível raiz e evita quebrar o processamento
            open_chats = fields_config.pop('open_chats', None)
            closed_chats = fields_config.pop('closed_chats', None)
            _ = fields_config.pop('type', None)  # ignorado aqui; controle de formato pode ser adicionado depois

            # [NOVO] Propaga flags para o modelo rooms, se existir
            if 'rooms' in fields_config and isinstance(fields_config['rooms'], dict):
                if isinstance(open_chats, bool):
                    fields_config['rooms']['open_chats'] = open_chats
                if isinstance(closed_chats, bool):
                    fields_config['rooms']['closed_chats'] = closed_chats

            # Estima o tempo de execução
            estimated_time = self._estimate_execution_time(fields_config, project)
            
            # Limite: só 1 relatório ativo (pending|processing) por projeto
            active_exists = ReportStatus.objects.filter(
                project=project,
                status__in=['pending', 'processing'],
            ).exists()

            if active_exists:
                return Response(
                    {
                        "error": {
                            "code": "max_report_limit",
                            "message": "Report in progress, please wait for it to finish or cancel it",
                            "limit": 1,
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Cria o objeto de status (pendente)
            report_status = ReportStatus.objects.create(
                project=project,
                user=request.user,
                fields_config=fields_config
            )

            minutes = max(1, (estimated_time + 59) // 60)
            logger.info("ReportStatus created (pending): %s project=%s", report_status.uuid, project.uuid)
            return Response(
                {
                    'time_request': f'{minutes}min',
                    'uuid_relatorio': str(report_status.uuid),
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            raise e
    
    def get(self, request):
        project_uuid = request.query_params.get('project_uuid')
        if not project_uuid:
            raise ValidationError({'project_uuid': 'This field is required.'})

        project = get_object_or_404(Project, uuid=project_uuid)

        report_status = ReportStatus.objects.filter(project=project).order_by('-created_on').first()
        if not report_status:
            return Response(
                {
                    'status': 'PENDING',
                    'email': None,
                    'uuid_relatorio': None,
                },
                status=status.HTTP_200_OK,
            )

        status_map = {'pending': 'PENDING', 'processing': 'IN_PROGRESS', 'completed': 'READY', 'failed': 'FAILED'}
        return Response({
            'status': status_map.get(report_status.status, 'PENDING'),
            'email': report_status.user.email if report_status.user.pk else None,
            'uuid_relatorio': str(report_status.uuid),
        }, status=status.HTTP_200_OK)
