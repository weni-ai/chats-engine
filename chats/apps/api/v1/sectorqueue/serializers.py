from rest_framework import serializers
from chats.apps.sectorqueue.models import SectorQueue, SectorQueueAuthorization

# Sector Queue serializers


class SectorQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorQueue
        fields = "__all__"


class SectorQueueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorQueue
        fields = "__all__"

        extra_kwargs = {field: {"required": False} for field in fields}


class SectorQueueReadOnlyListSerializer(serializers.ModelSerializer):
    agents = serializers.SerializerMethodField()

    class Meta:
        model = SectorQueue
        fields = ["uuid", "name", "agents"]

    def get_agents(self, sectorqueue: SectorQueue):
        return sectorqueue.agent_count


class SectorQueueAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorQueueAuthorization
        fields = "__all__"
