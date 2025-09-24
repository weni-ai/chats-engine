import io
import json
import logging

import pandas
import pendulum
from django.apps import apps
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
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
from chats.apps.dashboard.models import ReportStatus
from chats.apps.projects.models import Project, ProjectPermission
from chats.core.excel_storage import ExcelStorage

from .dto import Filters, should_exclude_admin_domains
from .presenter import ModelFieldsPresenter
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
from django.contrib.postgres.aggregates import ArrayAgg

logger = logging.getLogger(__name__)

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

    @action(detail=True, methods=["get"])
    def report_status(self, request, **kwargs):
        """Verifica o status de um relatório"""
        try:
            report_uuid = kwargs.get("uuid") or kwargs.get("pk")

            report_status = ReportStatus.objects.get(uuid=report_uuid)
            return Response(
                {
                    "status": report_status.status,
                    "error_message": report_status.error_message,
                }
            )
        except ReportStatus.DoesNotExist:
            return Response({"error": "Report not found"}, status=404)


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

    permission_classes = [permissions.IsAuthenticated]

    def _get_model_class(self, model_name):
        """
        Find the Django model class based on the name
        """
        model_mapping = {
            "sectors": ("sectors", "Sector"),
            "queues": ("queues", "Queue"),
            "rooms": ("rooms", "Room"),
            "users": ("accounts", "User"),
            "sector_tags": ("sectors", "SectorTag"),
            "contacts": ("contacts", "Contact"),
        }

        if model_name in model_mapping:
            app_label, model_class_name = model_mapping[model_name]
            try:
                return apps.get_model(app_label=app_label, model_name=model_class_name)
            except LookupError:
                pass

        common_apps = [
            "sectors",
            "msgs",
            "projects",
        ]
        for app in common_apps:
            try:
                return apps.get_model(app_label=app, model_name=model_name.capitalize())
            except LookupError:
                continue

        return None

    def _get_model_count_for_project(self, model_class, project):
        """
        Count records of a specific model for a project
        """
        try:
            model_fields = {
                field.name: field for field in model_class._meta.get_fields()
            }

            filters = Q()

            if "project" in model_fields:
                filters |= Q(project=project)
            if "sector" in model_fields:
                filters |= Q(sector__project=project)
            if "queue" in model_fields:
                filters |= Q(queue__sector__project=project)
            if "user" in model_fields:
                filters |= Q(user__project_permissions__project=project)

            if filters:
                return model_class.objects.filter(filters).distinct().count()
            else:
                total_count = model_class.objects.count()
                return max(1, total_count // 10)

        except Exception as e:
            logger.error(f"Erro ao contar registros para {model_class.__name__}: {e}")
            return 0

    def _estimate_execution_time(self, fields_config, project):
        """
        Estimate the execution time based on the volume of data that will be processed
        """
        available_models = ModelFieldsPresenter.get_models_info()
        invalid_models = [
            model for model in fields_config.keys() if model not in available_models
        ]

        if invalid_models:
            raise ValidationError(
                f"Models not available: {', '.join(invalid_models)}. "
                f"Models available: {', '.join(sorted(available_models.keys()))}"
            )

        total_records = 0
        processed_models = []

        for model_name in fields_config.keys():
            try:
                model_class = self._get_model_class(model_name)

                if model_class:
                    count = self._get_model_count_for_project(model_class, project)
                    total_records += count
                    processed_models.append({"model": model_name, "count": count})
                    logger.info(f"Model {model_name}: {count} records")
                else:
                    logger.warning(f"Model {model_name} not found")

            except Exception as e:
                logger.error(f"Error processing model {model_name}: {e}")
                continue

        base_time = 30
        time_per_1000_records = 45

        complexity_factor = 1 + (len(processed_models) * 0.1)

        if total_records > 0:
            estimated_time = (
                base_time + (total_records / 1000) * time_per_1000_records
            ) * complexity_factor
        else:
            estimated_time = base_time

        final_estimate = max(30, min(int(estimated_time), 600))

        logger.info(
            f"Estimated time: {final_estimate}s for {total_records} records in {len(processed_models)} models"
        )

        return final_estimate

    def _get_base_queryset(self, model_name, project):
        """
        Return the base queryset for any model returned by the ModelFieldsPresenter
        """
        available_fields = ModelFieldsPresenter.get_models_info()

        if model_name not in available_fields:
            raise NotFound(f'Model "{model_name}" not found')

        model = self._get_model_class(model_name)

        if model is None:
            raise NotFound(f'Model "{model_name}" not found')

        queryset = model.objects.all()

        if model_name == "sectors":
            queryset = queryset.filter(project=project)
        elif model_name == "queues":
            queryset = queryset.filter(sector__project=project)
        elif model_name == "rooms":
            queryset = queryset.filter(queue__sector__project=project)
        elif model_name == "contacts":
            queryset = queryset.filter(rooms__queue__sector__project=project).distinct()
        elif model_name == "users":
            queryset = queryset.filter(project_permissions__project=project).distinct()
        elif model_name == "sector_tags":
            queryset = queryset.filter(sector__project=project)

        return queryset

    def _process_model_fields(self, model_name, field_data, project, available_fields):
        """
        Process the fields of a model and its relationships
        """
        if model_name not in available_fields:
            raise NotFound(f'Model "{model_name}" not found')

        model_fields = available_fields[model_name]
        query_fields = []
        related_queries = {}

        for key, value in field_data.items():
            if key == "fields" and isinstance(value, list):
                invalid_fields = []
                for field in value:
                    if field in model_fields:
                        continue
                    if "__" in field:
                        base_field = field.split("__")[0]
                        if base_field in model_fields:
                            continue
                    invalid_fields.append(field)

                if invalid_fields:
                    raise NotFound(
                        f'Invalid fields for {model_name}: {", ".join(invalid_fields)}'
                    )
                query_fields.extend(value)
                if (
                    model_name == "rooms"
                    and "contact" in query_fields
                    and "contact__name" not in query_fields
                ):
                    query_fields = [
                        f if f != "contact" else "contact__name" for f in query_fields
                    ]
                if model_name == "rooms" and "queue" in query_fields:
                    query_fields = [
                        f if f != "queue" else "queue__name" for f in query_fields
                    ]
                if model_name == "rooms" and query_fields:
                    order_rank = {
                        "user__first_name": 1,
                        "user__last_name": 2,
                        "user__email": 3,
                        "queue__sector__name": 4,
                        "queue__name": 5,
                        "uuid": 6,
                        "contact__status": 7,
                        "is_active": 7,
                        "protocol": 8,
                        "tags": 9,
                        "created_on": 10,
                        "ended_at": 11,
                        "transfer_history": 12,
                        "contact__name": 13,
                        "contact__uuid": 14,
                        "urn": 15,
                        "custom_fields": 16,
                    }
                    query_fields = sorted(
                        query_fields, key=lambda f: order_rank.get(f, 999)
                    )
            elif key in available_fields:
                related_queries[key] = self._process_model_fields(
                    key, value, project, available_fields
                )

        base_queryset = self._get_base_queryset(model_name, project)

        uuids = field_data.get("uuids")
        if isinstance(uuids, list) and uuids:
            if "__all__" not in uuids:
                base_queryset = base_queryset.filter(uuid__in=uuids)

        if model_name == "rooms":
            open_chats = field_data.get("open_chats")
            closed_chats = field_data.get("closed_chats")
            if open_chats is True and closed_chats is True:
                raise ValidationError(
                    "open_chats and closed_chats cannot be used together."
                )

        if model_name == "rooms":
            start_date = field_data.get("start_date")
            end_date = field_data.get("end_date")
            if start_date and end_date:
                tz = project.timezone
                start_dt = pendulum.parse(start_date).replace(tzinfo=tz)
                end_dt = pendulum.parse(end_date + " 23:59:59").replace(tzinfo=tz)
                if open_chats is True:
                    base_queryset = base_queryset.filter(
                        created_on__range=[start_dt, end_dt]
                    )
                elif closed_chats and not open_chats:
                    base_queryset = base_queryset.filter(
                        is_active=False,
                        ended_at__range=[start_dt, end_dt],
                    )
                else:
                    base_queryset = base_queryset.filter(
                        Q(created_on__range=[start_dt, end_dt])
                        | Q(ended_at__range=[start_dt, end_dt])
                    )
        else:
            start_date = field_data.get("start_date")
            end_date = field_data.get("end_date")
            if start_date and end_date:
                try:
                    tz = project.timezone
                    start_dt = pendulum.parse(start_date).replace(tzinfo=tz)
                    end_dt = pendulum.parse(end_date + " 23:59:59").replace(tzinfo=tz)
                    model_obj = base_queryset.model
                    model_field_names = {f.name for f in model_obj._meta.get_fields()}
                    if "created_on" in model_field_names:
                        base_queryset = base_queryset.filter(
                            created_on__range=[start_dt, end_dt]
                        )
                except Exception:
                    pass

        if model_name == "rooms":

            def _norm_list(value):
                """
                Accepts: list/tuple/set, single str/uuid, dicts like {'uuids': [...]} or {'uuid': '...'}.
                Returns: flat list[str]. If contains "__all__", ignore the filter (return []).
                """
                if value is None:
                    return []
                if isinstance(value, (list, tuple, set)):
                    out = []
                    for item in value:
                        if isinstance(item, dict):
                            if "uuid" in item:
                                out.append(str(item["uuid"]))
                            elif "value" in item:
                                out.append(str(item["value"]))
                        else:
                            out.append(str(item))
                    if any(str(x).strip() == "__all__" for x in out):
                        return []
                    return out
                if isinstance(value, dict):
                    if "uuids" in value and isinstance(
                        value["uuids"], (list, tuple, set)
                    ):
                        vals = [str(v) for v in value["uuids"]]
                        return [] if any(v.strip() == "__all__" for v in vals) else vals
                    if "uuid" in value:
                        v = str(value["uuid"])
                        return [] if v.strip() == "__all__" else [v]
                    if "value" in value:
                        v = str(value["value"])
                        return [] if v.strip() == "__all__" else [v]
                    return []
                v = str(value)
                return [] if v.strip() == "__all__" else [v]

            sectors = _norm_list(field_data.get("sectors") or field_data.get("sector"))
            queues = _norm_list(field_data.get("queues") or field_data.get("queue"))
            agents = _norm_list(field_data.get("agents") or field_data.get("agent"))
            tags = _norm_list(field_data.get("tags") or field_data.get("tag"))

            if sectors:
                base_queryset = base_queryset.filter(queue__sector__uuid__in=sectors)
            if queues:
                base_queryset = base_queryset.filter(queue__uuid__in=queues)
            if agents:
                base_queryset = base_queryset.filter(user__uuid__in=agents)
            if tags:
                base_queryset = base_queryset.filter(tags__name__in=tags)

        if query_fields:
            if model_name == "rooms" and "tags" in query_fields:
                base_queryset = base_queryset.annotate(
                    tags_list=ArrayAgg("tags__name", distinct=True)
                )
                query_fields = ["tags_list" if f == "tags" else f for f in query_fields]
            base_queryset = base_queryset.values(*query_fields)

        return {"queryset": base_queryset, "related": related_queries}

    def _group_duplicate_records(self, raw_data):
        """
        Group duplicate records caused by Many-to-Many or ForeignKey reverse lookups
        """
        if not raw_data:
            return []

        sample_row = raw_data[0]
        group_fields = [key for key in sample_row.keys() if "__" not in key]
        lookup_fields = [key for key in sample_row.keys() if "__" in key]

        if not group_fields or not lookup_fields:
            return raw_data

        grouped_data = {}

        for row in raw_data:
            group_key = tuple(row.get(field) for field in group_fields)

            if group_key not in grouped_data:
                grouped_data[group_key] = {
                    field: row.get(field) for field in group_fields
                }
                for field in lookup_fields:
                    grouped_data[group_key][field] = []

            for field in lookup_fields:
                value = row.get(field)
                if value is not None and value not in grouped_data[group_key][field]:
                    grouped_data[group_key][field].append(value)

        result = list(grouped_data.values())

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

        if "queryset" in query_data:
            try:
                raw_data = list(query_data["queryset"])

                has_lookups = (
                    any("__" in str(key) for row in raw_data[:1] for key in row.keys())
                    if raw_data
                    else False
                )

                if has_lookups and raw_data:
                    result["data"] = self._group_duplicate_records(raw_data)
                else:
                    result["data"] = raw_data

            except Exception as e:
                raise ValidationError(f"Error executing query: {str(e)}")

        if "related" in query_data:
            for model, related_data in query_data["related"].items():
                result[model] = self._execute_queries(related_data)

        return result

    def _generate_report_data(self, data, project):
        """
        Internal method to generate the report data
        """
        available_fields = ModelFieldsPresenter.get_models_info()

        queries = {}
        for model_name, field_data in data.items():
            queries[model_name] = self._process_model_fields(
                model_name, field_data, project, available_fields
            )

        report_data = {}
        for model_name, query_data in queries.items():
            report_data[model_name] = self._execute_queries(query_data)

        return report_data

    def post(self, request):
        project_uuid = request.data.get("project_uuid")
        if not project_uuid:
            raise ValidationError({"project_uuid": "This field is required."})

        project = get_object_or_404(Project, uuid=project_uuid)

        active_exists = ReportStatus.objects.filter(
            project=project,
            status__in=["pending", "processing"],
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

        try:
            fields_config = {
                k: v for k, v in request.data.items() if k != "project_uuid"
            }

            def _is_true(v):
                if isinstance(v, bool):
                    return v
                if isinstance(v, str):
                    return v.strip().lower() in ("true", "1", "yes", "y", "on")
                if isinstance(v, int):
                    return v == 1
                return False

            open_chats = _is_true(fields_config.pop("open_chats", None))
            closed_chats = _is_true(fields_config.pop("closed_chats", None))
            file_type = fields_config.pop("type", None)
            root_start_date = fields_config.pop("start_date", None)
            root_end_date = fields_config.pop("end_date", None)

            if "rooms" in fields_config and isinstance(fields_config["rooms"], dict):
                fields_config["rooms"]["open_chats"] = open_chats
                fields_config["rooms"]["closed_chats"] = closed_chats
                if root_start_date and "start_date" not in fields_config["rooms"]:
                    fields_config["rooms"]["start_date"] = root_start_date
                if root_end_date and "end_date" not in fields_config["rooms"]:
                    fields_config["rooms"]["end_date"] = root_end_date

            root_sectors = request.data.get("sectors") or request.data.get("sector")
            root_queues = request.data.get("queues") or request.data.get("queue")
            root_agents = request.data.get("agents") or request.data.get("agent")
            root_tags = request.data.get("tags") or request.data.get("tag")
            if "rooms" not in fields_config or not isinstance(
                fields_config["rooms"], dict
            ):
                fields_config["rooms"] = {}
            if root_agents is not None:
                fields_config["rooms"]["agents"] = root_agents
            if root_tags is not None:
                fields_config["rooms"]["tags"] = root_tags

            fields_config = {"rooms": fields_config.get("rooms", {})}

            estimated_time = self._estimate_execution_time(fields_config, project)

            if file_type:
                fields_config["type"] = file_type
            report_status = ReportStatus.objects.create(
                project=project, user=request.user, fields_config=fields_config
            )

            minutes = max(1, (estimated_time + 59) // 60)
            logger.info(
                "ReportStatus created (pending): %s project=%s",
                report_status.uuid,
                project.uuid,
            )
            return Response(
                {
                    "time_request": f"{minutes}min",
                    "report_uuid": str(report_status.uuid),
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            raise e

    def get(self, request):
        project_uuid = request.query_params.get("project_uuid")
        if not project_uuid:
            raise ValidationError({"project_uuid": "This field is required."})

        project = get_object_or_404(Project, uuid=project_uuid)
        has_completed_export = ReportStatus.objects.filter(
            project=project, status="ready"
        ).exists()
        if not has_completed_export:
            return Response(
                {
                    "status": "ready",
                    "email": None,
                    "report_uuid": None,
                },
                status=status.HTTP_200_OK,
            )

        report_status = (
            ReportStatus.objects.filter(project=project).order_by("-created_on").first()
        )

        return Response(
            {
                "status": report_status.status,
                "email": report_status.user.email,
                "report_uuid": str(report_status.uuid),
            },
            status=status.HTTP_200_OK,
        )
