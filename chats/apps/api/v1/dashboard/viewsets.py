import io
import json

import pandas
from django.http import HttpResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

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
from chats.apps.api.v1.permissions import HasDashboardAccess
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


class DashboardLiveViewset(viewsets.GenericViewSet):
    lookup_field = "uuid"
    queryset = Project.objects.all()

    def get_permissions(self):
        permission_classes = [permissions.IsAuthenticated, HasDashboardAccess]
        return [permission() for permission in permission_classes]

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
            is_weni_admin=should_exclude_admin_domains(request.user.email if request.user else ""),
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
            is_weni_admin=should_exclude_admin_domains(request.user.email if request.user else ""),
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
            is_weni_admin=should_exclude_admin_domains(request.user.email if request.user else ""),
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
            is_weni_admin=should_exclude_admin_domains(request.user.email if request.user else ""),
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
            excel_rooms_buffer.seek(0)  # Move o cursor para o início do buffer
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
            is_weni_admin=should_exclude_admin_domains(request.user.email if request.user else ""),
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

            excel_buffer.seek(0)  # Move o cursor para o início do buffer
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


class ModelFieldsViewSet(APIView):
    """
    Endpoint para retornar os campos disponíveis dos principais models do sistema.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(ModelFieldsPresenter.get_models_info())


class ReportFieldsValidatorViewSet(APIView):
    """
    Endpoint para validar campos e gerar consulta para relatório baseado nos campos disponíveis.
    """
    permission_classes = [permissions.IsAuthenticated, HasDashboardAccess]

    def _get_base_queryset(self, model_name, project):
        """
        Retorna o queryset base para qualquer modelo retornado pelo ModelFieldsPresenter
        """
        available_fields = ModelFieldsPresenter.get_models_info()
        
        if model_name not in available_fields:
            raise ValidationError(f'Modelo "{model_name}" não encontrado')
            
        # Obtém o modelo real do Django
        try:
            common_apps = ['sectors', 'queues', 'rooms', 'accounts', 'contacts']
            model = None
            for app in common_apps:
                try:
                    model = apps.get_model(app_label=app, model_name=model_name.capitalize())
                    break
                except LookupError:
                    continue
            
            if model is None:
                raise ValidationError(f'Não foi possível encontrar o modelo para "{model_name}"')

        except LookupError:
            raise ValidationError(f'Modelo "{model_name}" não encontrado no sistema')

        # Constrói a query base
        return model.objects.all()

    def _process_model_fields(self, model_name, field_data, project, available_fields):
        """
        Processa os campos de um modelo e suas relações
        """
        if model_name not in available_fields:
            raise ValidationError(f'Modelo "{model_name}" não encontrado')

        model_fields = available_fields[model_name]
        query_fields = []
        related_queries = {}

        for key, value in field_data.items():
            if key == 'fields' and isinstance(value, list):
                # Valida campos diretos do modelo
                invalid_fields = [
                    field for field in value
                    if field not in model_fields
                ]
                if invalid_fields:
                    raise ValidationError(f'Campos inválidos para {model_name}: {", ".join(invalid_fields)}')
                query_fields.extend(value)
            elif key in available_fields:
                # Processa campos relacionados
                related_queries[key] = self._process_model_fields(key, value, project, available_fields)

        # Obtém o queryset base
        base_queryset = self._get_base_queryset(model_name, project)

        # Aplica os campos selecionados
        if query_fields:
            base_queryset = base_queryset.values(*query_fields)

        # Aplica filtros relacionados ao projeto
        try:
            base_queryset = base_queryset.filter(
                Q(project=project) |
                Q(sector__project=project) |
                Q(queue__sector__project=project) |
                Q(project_permissions__project=project)
            ).distinct()
        except Exception:
            # Se os filtros não funcionarem, mantém o queryset original
            pass

        return {
            'queryset': base_queryset,
            'related': related_queries
        }

    def _execute_queries(self, query_data):
        """
        Executa as queries e formata o resultado
        """
        result = {}
        
        if 'queryset' in query_data:
            try:
                result['data'] = list(query_data['queryset'])
            except Exception as e:
                raise ValidationError(f'Erro ao executar query: {str(e)}')

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

    def post(self, request):
        project_uuid = request.data.get('project_uuid')
        if not project_uuid:
            raise ValidationError({'project_uuid': 'Este campo é obrigatório.'})
        
        project = get_object_or_404(Project, uuid=project_uuid)
        
        try:
            # Remove project_uuid do processamento
            fields_config = {k: v for k, v in request.data.items() 
                           if k != 'project_uuid'}
            
            # Envia para processamento assíncrono
            generate_custom_fields_report.delay(
                project_uuid=project.uuid,
                fields_config=fields_config,
                user_email=request.user.email
            )
            
            return Response({
                'message': 'O relatório será enviado para seu email quando estiver pronto.',
                'status': 'processing'
            }, status=status.HTTP_202_ACCEPTED)
            
        except ValidationError as e:
            return Response(
                {'errors': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Erro inesperado: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )