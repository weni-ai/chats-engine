import json

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia


class MessageSerializer(serializers.ModelSerializer):
    # media = serializers.FileField(use_url=True, required=False)

    class Meta:
        model = ChatMessage
        fields = ["room", "user", "contact", "text", "seen", "medias"]
        read_only_fields = [
            "created_at",
        ]

    def create(self, validated_data):
        instance = super().create(validated_data)
        if validated_data.get("media_file"):
            instance.media.create(medias=validated_data.get("media_file"))
        return

    # def get_media(self, msg):
    #     media_url = msg.media.url
    #     return media_url


class MessageWSSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = "__all__"


class MessageMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageMedia
        fields = "__all__"
