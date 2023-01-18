from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from chats.apps.api.v1.permissions import IsSectorManager

from chats.apps.projects.models import Project
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


from chats.apps.api.v1.dashboard.serializers import (
    DashboardRoomsSerializer,
    DashboardAgentsSerializer,
    DashboardSectorSerializer,
)


class DashboardLiveViewset(viewsets.GenericViewSet):
    lookup_field = "uuid"
    queryset = Project.objects.all()

    def get_permissions(self):
        permission_classes = [permissions.IsAuthenticated, IsSectorManager]
        return [permission() for permission in permission_classes]

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
