import json

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, exceptions

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia
from chats.apps.accounts.models import User


class MessageMediaSimpleSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MessageMedia
        fields = [
            "content_type",
            "message",
            "media_file",
            "url",
            "created_on",
        ]

        extra_kwargs = {
            "media_file": {"write_only": True},
            "message": {"read_only": True, "required": False},
        }

    def get_url(self, media: MessageMedia):
        return media.url

    def get_sender(self, media: MessageMedia):
        return media.message.get_sender().full_name


class MessageMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)
    sender = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MessageMedia
        fields = [
            "sender",
            "content_type",
            "message",
            "media_file",
            "url",
            "created_on",
        ]

        extra_kwargs = {
            "media_file": {"write_only": True},
        }

    def get_url(self, media: MessageMedia):
        return media.url

    def get_sender(self, media: MessageMedia):
        return media.message.get_sender().full_name


class BaseMessageSerializer(serializers.ModelSerializer):
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
    text = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=""
    )

    def create(self, validated_data):
        room = validated_data.get("room")
        if room.is_waiting is True:
            raise exceptions.APIException(
                detail="Cannot create message when the room is waiting for contact's answer"
            )

        msg = super().create(validated_data)
        return msg


class MessageSerializer(BaseMessageSerializer):
    """Serializer for the messages endpoint"""

    media = MessageMediaSimpleSerializer(many=True, required=False)

    class Meta:
        model = ChatMessage
        fields = [
            "uuid",
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
            "uuid",
            "user",
            "created_on",
            "contact",
        ]

    def create(self, validated_data):
        room = validated_data.get("room")
        if room.is_waiting is True:
            raise exceptions.APIException(
                detail="Cannot create message when the room is waiting for contact's answer"
            )

        msg = super().create(validated_data)
        return msg


class MessageWSSerializer(MessageSerializer):
    pass
