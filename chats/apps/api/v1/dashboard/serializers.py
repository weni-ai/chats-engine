from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from timezone_field.rest_framework import TimeZoneSerializerField
from chats.apps.projects.models import Project

from chats.apps.rooms.models import Room
from chats.apps.api.v1.internal.users.serializers import UserSerializer
from django.db.models import Count, Avg, F, Sum


class DashboardRoomsSerializer(serializers.ModelSerializer):

    active_chats = serializers.SerializerMethodField()
    interact_time = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "active_chats",
            "interact_time"
        ]

    def get_active_chats(self, project):
        return  Room.objects.filter(queue__sector__project=project, is_active=True).count()

    # def get_waiting_time(self, project):


    def get_interact_time(self, project):
        interation_time = Room.objects.filter(queue__sector__project=project, is_active=True, ended_at__isnull=False).aggregate(
            avg_time=Sum(
                F('ended_at') - F('created_on'),
                )       
            )
        minutes = interation_time["avg_time"].total_seconds()
        return round(minutes, 2)




