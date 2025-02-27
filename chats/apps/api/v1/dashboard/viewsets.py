import io
import json

import pandas
from django.http import HttpResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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

from .dto import Filters
from .service import AgentsService, RawDataService, RoomsDataService, SectorService


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

        user_permission = ProjectPermission.objects.get(
            user=request.user, project=project
        )
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
            is_weni_admin=(
                True if request.user and "weni.ai" in request.user.email else False
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
            is_weni_admin=(
                True if request.user and "weni.ai" in request.user.email else False
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

        user_permission = ProjectPermission.objects.get(
            user=request.user, project=project
        )
        filters = Filters(
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            agent=params.get("agent"),
            sector=params.get("sector"),
            queue=params.get("queue"),
            tag=params.get("tag"),
            user_request=user_permission,
            project=project,
            is_weni_admin=(
                True if request.user and "weni.ai" in request.user.email else False
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
        user_permission = ProjectPermission.objects.get(
            user=request.user, project=project
        )
        filters = Filters(
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            agent=params.get("agent"),
            sector=params.get("sector"),
            queue=params.get("queue"),
            tag=params.get("tag"),
            user_request=user_permission,
            project=project,
            is_weni_admin=(
                True if request.user and "weni.ai" in request.user.email else False
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
        user_permission = ProjectPermission.objects.get(
            user=request.user, project=project
        )
        filters = Filters(
            start_date=filter.get("start_date"),
            end_date=filter.get("end_date"),
            agent=filter.get("agent"),
            sector=filter.get("sector"),
            queue=filter.get("queue"),
            tag=filter.get("tag"),
            user_request=user_permission,
            project=project,
            is_weni_admin=(
                True if request.user and "weni.ai" in request.user.email else False
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
