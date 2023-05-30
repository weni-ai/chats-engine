import pandas
from django.http import HttpResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.api.v1.dashboard.presenter import (
    get_agents_data,
    get_export_data,
    get_general_data,
    get_sector_data,
)
from chats.apps.api.v1.dashboard.serializers import (
    DashboardRawDataSerializer,
    dashboard_general_data,
    dashboard_agents_data,
    dashboard_division_data,
)
from chats.apps.api.v1.permissions import HasDashboardAccess
from chats.apps.projects.models import Project


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
        filters = request.query_params
        serialized_data = dashboard_general_data(
            project=project,
            context=filters,
        )
        return Response(serialized_data, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        url_name="agent",
    )
    def agent(self, request, *args, **kwargs):
        """Agent metrics for the project or the sector"""
        project = self.get_object()
        context = request.query_params
        context["is_weni_admin"] = (
            True if request.user and "weni.ai" in request.user.email else False
        )
        serialized_data = dashboard_agents_data(
            instance=project,
            context=context,
        )
        return Response(serialized_data, status.HTTP_200_OK)

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
        filters = request.query_params
        serialized_data = dashboard_division_data(
            instance=project,
            context=filters,
        )
        return Response(serialized_data, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        url_name="raw",
        serializer_class=DashboardRawDataSerializer,
    )
    def raw_data(self, request, *args, **kwargs):
        """Raw data for the project, sector, queue and agent."""
        project = self.get_object()
        filters = request.query_params
        serialized_data = self.get_serializer(
            instance=project,
            context=filters,
        )
        return Response(serialized_data.data, status.HTTP_200_OK)

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

        filename = "dashboard_export_data"

        if "xls" in filter:
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = (
                'attachment; filename="' + filename + ".xls"
            )
        else:
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="' + filename + ".csv"
            )

        table = pandas.DataFrame(dataset)
        table.rename(
            columns={
                0: "Queue Name",
                1: "Waiting Time",
                2: "Response Time",
                3: "Interaction Time",
                4: "Open",
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

        general_dataset = get_general_data(project, filter)
        userinfo_dataset = get_agents_data(project, filter)
        sector_dataset = get_sector_data(project, filter)

        filename = "dashboard_export_data"

        data_frame = pandas.DataFrame([general_dataset])
        data_frame_1 = pandas.read_json(userinfo_dataset)
        data_frame_2 = pandas.read_json(sector_dataset)

        if "xls" in filter:
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = (
                'attachment; filename="' + filename + ".xlsx"
            )
            with pandas.ExcelWriter(response, engine="xlsxwriter") as writer:
                data_frame.to_excel(
                    writer,
                    sheet_name="dashboard_infos",
                    startrow=1,
                    startcol=0,
                    index=False,
                )
                data_frame_1.to_excel(
                    writer,
                    sheet_name="dashboard_infos",
                    startrow=4 + len(data_frame.index),
                    startcol=0,
                    index=False,
                )
                data_frame_2.to_excel(
                    writer,
                    sheet_name="dashboard_infos",
                    startrow=8 + len(data_frame_1.index),
                    startcol=0,
                    index=False,
                )
            return response

        else:
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="' + filename + ".csv"
            )

            data_frame.to_csv(response, index=False)
            data_frame_1.to_csv(response, index=False, mode="a")
            data_frame_2.to_csv(response, index=False, mode="a")

            return response
