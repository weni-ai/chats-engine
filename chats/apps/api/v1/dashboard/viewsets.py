from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from chats.apps.api.v1.permissions import IsSectorManager

from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector, SectorTag
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


from chats.apps.api.v1.dashboard.serializers import (
    DashboardRoomsSerializer,
    DashboardAgentsSerializer,
    DashboardSectorSerializer,
    DashboardTagRoomFilterSerializer,
    DashboardTagAgentFilterSerializer,
    DashboardTagQueueFilterSerializer,
    DashboardSectorFilterSerializer,
    DashboardSectorAgentFilterSerializer,
    DashboardSectorQueueFilterSerializer,
    DashboardDateSectorFilterSerializer,
    DashboardDateSectorSerializer,
    DashboardDateAgentsSectorFilterSerializer,
    DashboardDateAgentsProjectFilterSerializer,
    DashboardDateQueueSerializer,
    DashboardDateProjectFilterSerializer,
)


class DashboardLiveViewset(viewsets.ViewSet):
    def get_permissions(self):
        permission_classes = [permissions.IsAuthenticated, IsSectorManager]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["GET"], url_name="rooms_info")
    def rooms_info(self, request, *args, **kwargs):
        try:
            project = Project.objects.get(pk=request.query_params["project"])
            serialized_data = DashboardRoomsSerializer(instance=project)
            return Response(serialized_data.data, status.HTTP_200_OK)
        except AttributeError:
            raise ValidationError({"detail": _("Project UUID not provided.")})

    @action(detail=False, methods=["GET"], url_name="agents_info")
    def agents_info(self, request, *args, **kwargs):
        try:
            project = Project.objects.get(pk=request.query_params["project"])
            serialized_data = DashboardAgentsSerializer(instance=project.pk)
            return Response(serialized_data.data, status.HTTP_200_OK)
        except AttributeError:
            raise ValidationError({"detail": _("Project UUID not provided.")})

    @action(detail=False, methods=["GET"], url_name="sectors_info")
    def sectors_info(self, request, *args, **kwargs):
        try:
            project = Project.objects.get(pk=request.query_params["project"])
            serialized_data = DashboardSectorSerializer(instance=project.pk)
            return Response(serialized_data.data, status.HTTP_200_OK)
        except AttributeError:
            raise ValidationError({"detail": _("Project UUID not provided.")})


class DashboardTagViewset(viewsets.ViewSet):
    def get_permissions(self):
        permission_classes = [permissions.IsAuthenticated, IsSectorManager]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["GET"], url_name="rooms_info")
    def rooms_info(self, request, *args, **kwargs):
        try:
            sector_tag = SectorTag.objects.get(
                sector=request.query_params["sector"], name=request.query_params["name"]
            )
            serialized_data = DashboardTagRoomFilterSerializer(instance=sector_tag)
            return Response(serialized_data.data, status.HTTP_200_OK)
        except AttributeError:
            raise ValidationError({"detail": _("Sector Tag UUID not provided.")})

    @action(detail=False, methods=["GET"], url_name="agents_info")
    def agents_info(self, request, *args, **kwargs):
        try:
            sector_tag = Sector.objects.get(pk=request.query_params["sector"])
            serialized_data = DashboardTagAgentFilterSerializer(
                instance=sector_tag,
                context={
                    "name": request.query_params["name"],
                },
            )
            return Response(serialized_data.data, status.HTTP_200_OK)
        except AttributeError:
            raise ValidationError({"detail": _("Sector Tag UUID not provided.")})

    @action(detail=False, methods=["GET"], url_name="queue_info")
    def queue_info(self, request, *args, **kwargs):
        try:
            sector_tag = SectorTag.objects.get(
                sector=request.query_params["sector"], name=request.query_params["name"]
            )
            serialized_data = DashboardTagQueueFilterSerializer(instance=sector_tag)
            return Response(serialized_data.data, status.HTTP_200_OK)
        except AttributeError:
            raise ValidationError({"detail": _("Sector Tag UUID not provided.")})


class DashboardSectorViewset(viewsets.ViewSet):
    def get_permissions(self):
        permission_classes = [permissions.IsAuthenticated, IsSectorManager]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["GET"], url_name="rooms_info")
    def rooms_info(self, request, *args, **kwargs):
        try:
            sector = Sector.objects.get(uuid=request.query_params["sector"])
            serialized_data = DashboardSectorFilterSerializer(instance=sector)
            return Response(serialized_data.data, status.HTTP_200_OK)
        except AttributeError:
            raise ValidationError({"detail": _("Sector UUID not provided.")})

    @action(detail=False, methods=["GET"], url_name="agents_info")
    def agents_info(self, request, *args, **kwargs):
        try:
            sector = Sector.objects.get(uuid=request.query_params["sector"])
            serialized_data = DashboardSectorAgentFilterSerializer(instance=sector)
            return Response(serialized_data.data, status.HTTP_200_OK)
        except AttributeError:
            raise ValidationError({"detail": _("Sector UUID not provided.")})

    @action(detail=False, methods=["GET"], url_name="queue_info")
    def queue_info(self, request, *args, **kwargs):
        try:
            sector = Sector.objects.get(pk=request.query_params["sector"])
            serialized_data = DashboardSectorQueueFilterSerializer(instance=sector.pk)
            return Response(serialized_data.data, status.HTTP_200_OK)
        except AttributeError:
            raise ValidationError({"detail": _("Sector UUID not provided.")})


class DashboardDateRangeViewset(viewsets.ViewSet):
    def get_permissions(self):
        permission_classes = [permissions.IsAuthenticated, IsSectorManager]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["GET"], url_name="rooms_info")
    def rooms_info(self, request, *args, **kwargs):
        try:
            if "sector" in request.query_params:
                sector = Sector.objects.get(pk=request.query_params["sector"])
                serialized_data = DashboardDateSectorFilterSerializer(
                    instance=sector.pk,
                    context={
                        "start_date": request.query_params["start_date"],
                        "end_date": request.query_params["end_date"],
                    },
                )
            elif "project" in request.query_params:
                project = Project.objects.get(pk=request.query_params["project"])
                serialized_data = DashboardDateProjectFilterSerializer(
                    instance=project.pk,
                    context={
                        "start_date": request.query_params["start_date"],
                        "end_date": request.query_params["end_date"],
                    },
                )

            return Response(serialized_data.data, status.HTTP_200_OK)

        except AttributeError:
            raise ValidationError({"detail": _("Sector or Project UUID not provided.")})

    @action(detail=False, methods=["GET"], url_name="agents_info")
    def agents_info(self, request, *args, **kwargs):
        try:
            if "sector" in request.query_params:
                sector = Sector.objects.get(pk=request.query_params["sector"])
                serialized_data = DashboardDateAgentsSectorFilterSerializer(
                    instance=sector.pk,
                    context={
                        "start_date": request.query_params["start_date"],
                        "end_date": request.query_params["end_date"],
                    },
                )
            elif "project" in request.query_params:
                project = Project.objects.get(pk=request.query_params["project"])
                serialized_data = DashboardDateAgentsProjectFilterSerializer(
                    instance=project.pk,
                    context={
                        "start_date": request.query_params["start_date"],
                        "end_date": request.query_params["end_date"],
                    },
                )
            return Response(serialized_data.data, status.HTTP_200_OK)

        except AttributeError:
            raise ValidationError({"detail": _("Sector or Project UUID not provided.")})

    @action(detail=False, methods=["GET"], url_name="queue_info")
    def queue_info(self, request, *args, **kwargs):
        try:
            if "sector" in request.query_params:
                sector = Sector.objects.get(pk=request.query_params["sector"])
                serialized_data = DashboardDateQueueSerializer(
                    instance=sector.pk,
                    context={
                        "start_date": request.query_params["start_date"],
                        "end_date": request.query_params["end_date"],
                    },
                )
            elif "project" in request.query_params:
                project = Project.objects.get(pk=request.query_params["project"])
                serialized_data = DashboardDateSectorSerializer(
                    instance=project.pk,
                    context={
                        "start_date": request.query_params["start_date"],
                        "end_date": request.query_params["end_date"],
                    },
                )
            return Response(serialized_data.data, status.HTTP_200_OK)

        except ValidationError:
            raise ValidationError({"detail": _("Sector or Project UUID not provided.")})
