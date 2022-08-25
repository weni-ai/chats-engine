import json

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia


class MessageSerializer(serializers.ModelSerializer):
    media = serializers.FileField(required=False)

    class Meta:
        model = ChatMessage
        fields = [
            "room",
            "user",
            "contact",
            "text",
            "seen",
            "media",
            "created_on",
        ]
        read_only_fields = [
            "created_at",
            "contact",
        ]

    def get_media(self, msg):
        try:
            return msg.media.url
        except AttributeError:
            return None


class MessageWSSerializer(MessageSerializer):
    pass


class MessageMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageMedia
        fields = "__all__"
