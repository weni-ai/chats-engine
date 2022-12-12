from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from chats.apps.msgs.models import Message
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.api.v1.dashboard.serializers import (
    DashboardRoomsSerializer, DashboardAgentsSerializer, DashboardSectorSerializer, 
    DashboardRoomFilterTagSerializer)
from django.db.models import Count, F, Avg, Sum

from chats.apps.sectors.models import SectorTag


class DashboardViewset(viewsets.ReadOnlyModelViewSet):

    @action(detail=False, methods=["GET"], url_name="rooms_info")
    def rooms_info(
        self, request, *args, **kwargs
    ):
        project = Project.objects.get(pk=request.query_params["project"])
        serialized_data = DashboardRoomsSerializer(instance=project)
        return Response(serialized_data.data, status.HTTP_200_OK)


    @action(detail=False, methods=["GET"], url_name="agents_info")
    def agents_info(
        self, request, *args, **kwargs
    ):
        project = Project.objects.get(pk=request.query_params["project"])
        serialized_data = DashboardAgentsSerializer(instance=project.pk)
        return Response(serialized_data.data, status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_name="sectors_info")
    def sectors_info(
        self, request, *args, **kwargs
    ):
        project = Project.objects.get(pk=request.query_params["project"])
        serialized_data = DashboardSectorSerializer(instance=project.pk)
        return Response(serialized_data.data, status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_name="rooms_filter_tag")
    def rooms_filter_tag(
        self, request, *args, **kwargs
    ):
        sector_tag = SectorTag.objects.get(sector=request.query_params["sector"], name=request.query_params["name"])
        serialized_data = DashboardRoomFilterTagSerializer(instance=sector_tag)
        return Response(serialized_data.data, status.HTTP_200_OK)