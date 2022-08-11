from rest_framework import serializers
from chats.apps.queues.models import Queue, QueueAuthorization

# Sector Queue serializers


class SectorQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = "__all__"


class SectorQueueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = "__all__"

        extra_kwargs = {field: {"required": False} for field in fields}


class SectorQueueReadOnlyListSerializer(serializers.ModelSerializer):
    agents = serializers.SerializerMethodField()

    class Meta:
        model = Queue
        fields = ["uuid", "name", "agents"]

    def get_agents(self, sectorqueue: Queue):
        return sectorqueue.agent_count


class SectorQueueAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueAuthorization
        fields = "__all__"
