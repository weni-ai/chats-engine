from rest_framework import serializers
from chats.apps.queues.models import Queue, QueueAuthorization

# Sector Queue serializers


class QueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = "__all__"


class QueueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = "__all__"

        extra_kwargs = {field: {"required": False} for field in fields}


class QueueReadOnlyListSerializer(serializers.ModelSerializer):
    agents = serializers.SerializerMethodField()

    class Meta:
        model = Queue
        fields = ["uuid", "name", "agents"]

    def get_agents(self, queue: Queue):
        return queue.agent_count


class QueueAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueAuthorization
        fields = "__all__"


class QueueAuthorizationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueAuthorization
        fields = "__all__"

        extra_kwargs = {field: {"required": False} for field in fields}


class QueueAuthorizationReadOnlyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueAuthorization
        fields = ["id", "uuid", "queue", "role", "user"]
