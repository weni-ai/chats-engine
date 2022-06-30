from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.sectors.models import Sector, SectorPermission


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = "__all__"


class SectorWSSerializer(serializers.ModelSerializer):
    """
    used to serialize data for the websocket connection
    """

    class Meta:
        model = Sector
        fields = "__all__"


class SectorPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorPermission
        fields = "__all__"


class SectorPermissionWSSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorPermission
        fields = "__all__"
