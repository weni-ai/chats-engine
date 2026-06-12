from rest_framework import serializers

from chats.apps.quickmessages.models import QuickMessage


class QuickMessageResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickMessage
        fields = ["uuid", "title", "shortcut", "text"]
        read_only_fields = fields
