from rest_framework import serializers

from chats.apps.queues.models import Queue


class QueueFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = [
            "uuid",
            "name",
        ]
