from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from chats.apps.msgs.models import Message
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room
from chats.apps.api.v1.dashboard.serializers import DashboardRoomsSerializer
from django.db.models import Count, F, Avg, Sum


class DashboardViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = DashboardRoomsSerializer

    @action(detail=False, methods=["GET"], url_name="rooms_info")
    def rooms_info(
        self, request, *args, **kwargs
    ):
        project = Project.objects.get(pk=request.query_params["project"])
        serialized_data = DashboardRoomsSerializer(instance=project)
        return Response(serialized_data.data, status.HTTP_200_OK)