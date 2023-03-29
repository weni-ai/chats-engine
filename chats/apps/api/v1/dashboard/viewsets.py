from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from chats.apps.api.v1.permissions import HasDashboardAccess

from chats.apps.projects.models import Project
from django.utils.translation import gettext_lazy as _

from chats.apps.api.v1.dashboard.presenter import get_export_data

import pandas

from django.http import HttpResponse


from chats.apps.api.v1.dashboard.serializers import (
    DashboardRoomsSerializer,
    DashboardAgentsSerializer,
    DashboardSectorSerializer,
)


class DashboardLiveViewset(viewsets.GenericViewSet):
    lookup_field = "uuid"
    queryset = Project.objects.all()

    # def get_permissions(self):
    #     permission_classes = [permissions.IsAuthenticated, HasDashboardAccess]
    #     return [permission() for permission in permission_classes]

    @action(
        detail=True,
        methods=["GET"],
        url_name="general",
        serializer_class=DashboardRoomsSerializer,
    )
    def general(self, request, *args, **kwargs):
        """General metrics for the project or the sector"""
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
        url_name="agent",
        serializer_class=DashboardAgentsSerializer,
    )
    def agent(self, request, *args, **kwargs):
        """Agent metrics for the project or the sector"""
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
        url_name="division",
        serializer_class=DashboardSectorSerializer,
    )
    def division(self, request, *args, **kwargs):
        """
        Can return data on project and sector level (list of sector or list of queues)
        """
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
