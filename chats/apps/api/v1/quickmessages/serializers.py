from rest_framework import serializers

from chats.apps.quickmessages.models import QuickMessage


class QuickMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickMessage
        fields = (
            "uuid",
            "created_on",
            "modified_on",
            "user",
            "shortcut",
            "text",
            "sector",
        )
        read_only_fields = ("user",)
