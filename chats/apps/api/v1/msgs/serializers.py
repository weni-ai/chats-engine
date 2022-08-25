import json

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia
from chats.apps.accounts.models import User


class MessageSerializer(serializers.ModelSerializer):
    media = serializers.FileField(required=False)
    contact = ContactSerializer(many=False, required=False, read_only=True)
    user = UserSerializer(many=False, required=False, read_only=True)
    user_email = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        required=False,
        source="user",
        slug_field="email",
        write_only=True,
        allow_null=True,
    )

    class Meta:
        model = ChatMessage
        fields = [
            "user_email",
            "user",
            "room",
            "contact",
            "text",
            "seen",
            "media",
            "created_on",
        ]
        read_only_fields = [
            "user",
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
