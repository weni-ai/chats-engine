from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.conf import settings

from chats.apps.sectors.models import Sector


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = "__all__"
