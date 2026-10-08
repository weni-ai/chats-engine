from rest_framework import serializers

from chats.apps.queues.models import Queue


class QueueFlowSerializer(serializers.ModelSerializer):
    """
    Serializer for queue data via external API.

    Returns the queue UUID and name.
    """

    class Meta:
        model = Queue
        fields = [
            "uuid",
            "name",
            "queue_purpose",
        ]
        extra_kwargs = {
            "uuid": {"help_text": "Unique identifier of the queue"},
            "name": {"help_text": "Display name of the queue"},
            "queue_purpose": {"help_text": "Description of the queue purpose"},
        }
