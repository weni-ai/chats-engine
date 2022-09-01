from rest_framework import serializers

from chats.apps.sectors.models import Sector


class SectorFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = [
            "uuid",
            "name",
        ]
