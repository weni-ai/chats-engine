from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import QueueAuthorization

from chats.apps.rooms.models import Room
from django.db.models import F, Sum, Count, Q


class DashboardRoomsSerializer(serializers.ModelSerializer):

    active_chats = serializers.SerializerMethodField()
    interact_time = serializers.SerializerMethodField()
    response_time = serializers.SerializerMethodField()
    waiting_time = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "active_chats",
            "interact_time",
            "response_time",
            "waiting_time"
        ]

    def get_active_chats(self, project):
        return Room.objects.filter(queue__sector__project=project, is_active=True).count()

    def get_interact_time(self, project):
        interation_time = Room.objects.filter(queue__sector__project=project, is_active=True, ended_at__isnull=False).aggregate(
            avg_time=Sum(
                F('ended_at') - F('created_on'),
                )       
            )
        minutes = interation_time["avg_time"].total_seconds()
        return round(minutes, 2)


    def get_response_time(self, project):
        metrics_rooms_count = RoomMetrics.objects.filter(room__queue__sector__project=project).count()
        
        room_metric = RoomMetrics.objects.filter(room__queue__sector__project=project).aggregate(message_response_time=Sum('message_response_time'))["message_response_time"]
        response_time = room_metric/metrics_rooms_count

        return response_time
        
    def get_waiting_time(self, project):
        metrics_rooms_count = RoomMetrics.objects.filter(room__queue__sector__project=project).count()
        
        room_metric = RoomMetrics.objects.filter(room__queue__sector__project=project).aggregate(waiting_time=Sum('waiting_time'))["waiting_time"]
        response_time = room_metric/metrics_rooms_count

        return response_time


class DashboardAgentsSerializer(serializers.ModelSerializer):

    project_agents = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "project_agents",
        ]

    def get_project_agents(self, project):
        
        queue_auth = QueueAuthorization.objects.filter(queue__sector__project=project, queue__sector__project__permissions__status="OFFLINE").values(
            "permission__user__first_name").annotate(
            count=Count("queue__rooms", filter=Q(queue__rooms__is_active=True), distinct=True))      

        return queue_auth
