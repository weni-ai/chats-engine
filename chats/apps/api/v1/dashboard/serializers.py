from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models import Project

from chats.apps.rooms.models import Room
from django.db.models import F, Sum


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
        metrics_rooms = RoomMetrics.objects.filter(room__queue__sector__project=project)
        metrics_rooms_count = RoomMetrics.objects.filter(room__queue__sector__project=project).count()
        response_time_avg = 0
        
        for i in metrics_rooms:
            response_time_avg += i.message_response_time

        response_time = response_time_avg/metrics_rooms_count

        return response_time
        
    def get_waiting_time(self, project):
        metrics_rooms = RoomMetrics.objects.filter(room__queue__sector__project=project)
        metrics_rooms_count = RoomMetrics.objects.filter(room__queue__sector__project=project).count()
        waiting_time_avg = 0
        
        for i in metrics_rooms:
            waiting_time_avg += i.waiting_time

        response_time = waiting_time_avg/metrics_rooms_count

        return response_time


class DashboardAgentsSerializer(serializers.ModelSerializer):
    
    online_agents = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            "online_agents",
        ]