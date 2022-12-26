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
    DashboardTagRoomFilterSerializer,DashboardTagAgentFilterSerializer, DashboardTagSectorFilterSerializer, 
    DashboardSectorFilterSerializer,DashboardSectorAgentFilterSerializer,DashboardSectorQueueFilterSerializer,
    DashboardDateSectorFilterSerializer, DashboardDateAgentsFilterSerializer, DashboardDateSectorSerializer)
from django.db.models import Count, F, Avg, Sum

from chats.apps.sectors.models import Sector, SectorTag


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
    def rooms_tag_filter(
        self, request, *args, **kwargs
    ):
        sector_tag = SectorTag.objects.get(sector=request.query_params["sector"], name=request.query_params["name"])
        serialized_data = DashboardTagRoomFilterSerializer(instance=sector_tag)
        return Response(serialized_data.data, status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_name="rooms_tag_agent_filter")
    def rooms_tag_agent_filter(
        self, request, *args, **kwargs
    ):
        sector_tag = SectorTag.objects.get(sector=request.query_params["sector"], name=request.query_params["name"])
        serialized_data = DashboardTagAgentFilterSerializer(instance=sector_tag)
        return Response(serialized_data.data, status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_name="rooms_tag_sector_filter")
    def rooms_tag_sector_filter(
        self, request, *args, **kwargs
    ):
        sector_tag = SectorTag.objects.get(sector=request.query_params["sector"], name=request.query_params["name"])
        serialized_data = DashboardTagSectorFilterSerializer(instance=sector_tag)
        return Response(serialized_data.data, status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_name="rooms_filter_sector")
    def rooms_sector_filter(
        self, request, *args, **kwargs
    ):
        sector = Sector.objects.get(uuid=request.query_params["sector"])
        serialized_data = DashboardSectorFilterSerializer(instance=sector)
        return Response(serialized_data.data, status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_name="rooms_sector_agent_filter")
    def rooms_sector_agent_filter(
        self, request, *args, **kwargs
    ):
        sector = Sector.objects.get(uuid=request.query_params["sector"])
        serialized_data = DashboardSectorAgentFilterSerializer(instance=sector)
        return Response(serialized_data.data, status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_name="rooms_sector_queues_filter")
    def rooms_sector_queues_filter(
        self, request, *args, **kwargs
    ):
        sector = Sector.objects.get(pk=request.query_params["sector"])
        serialized_data = DashboardSectorQueueFilterSerializer(instance=sector.pk)
        return Response(serialized_data.data, status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_name="rooms_date_sector_filter")
    def rooms_date_sector_filter(
        self, request, *args, **kwargs
    ):
        project = Sector.objects.get(pk=request.query_params["sector"])
        serialized_data = DashboardDateSectorFilterSerializer(instance=project.pk, context={"start_date": request.query_params["start_date"], "end_date": request.query_params["end_date"]})
        return Response(serialized_data.data, status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_name="rooms_date_agents_filter")
    def rooms_date_agents_filter(
        self, request, *args, **kwargs
    ):
        project = Sector.objects.get(pk=request.query_params["sector"])
        serialized_data = DashboardDateAgentsFilterSerializer(instance=project.pk, context={"start_date": request.query_params["start_date"], "end_date": request.query_params["end_date"]})
        return Response(serialized_data.data, status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_name="rooms_date_sector_filter")
    def rooms_date_sector_filter(
        self, request, *args, **kwargs
    ):
        project = Sector.objects.get(pk=request.query_params["sector"])
        serialized_data = DashboardDateSectorSerializer(instance=project.pk, context={"start_date": request.query_params["start_date"], "end_date": request.query_params["end_date"]})
        return Response(serialized_data.data, status.HTTP_200_OK)