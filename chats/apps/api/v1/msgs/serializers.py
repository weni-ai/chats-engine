import magic
import io

from pydub import AudioSegment

from django.conf import settings
from rest_framework import serializers, exceptions

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia
from chats.apps.accounts.models import User

"""
TODO: Refactor these serializers into less classes
"""


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
        try:
            return media.message.get_sender().full_name
        except AttributeError:
            return ""


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
        try:
            return media.message.get_sender().full_name
        except AttributeError:
            return ""

    def create(self, validated_data):
        media = validated_data["media_file"]
        file_bytes = media.file.read()
        file_type = magic.from_buffer(file_bytes, mime=True)

        if (
            file_type.startswith("audio")
            or file_type.lower() in settings.UNPERMITTED_AUDIO_TYPES
        ):

            export_conf = {"format": settings.AUDIO_TYPE_TO_CONVERT}
            if settings.AUDIO_CODEC_TO_CONVERT != "":
                export_conf["codec"] = settings.AUDIO_CODEC_TO_CONVERT

            converted_bytes = io.BytesIO()
            AudioSegment.from_file(io.BytesIO(file_bytes)).export(
                converted_bytes, **export_conf
            )

            media.file = converted_bytes
            media.name = media.name[:-3] + settings.AUDIO_EXTENSION_TO_CONVERT
            file_type = magic.from_buffer(converted_bytes.read(), mime=True)

        validated_data["content_type"] = file_type
        msg = super().create(validated_data)
        return msg


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


class MessageAndMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)
    sender = serializers.SerializerMethodField(read_only=True)
    message = BaseMessageSerializer(many=False)

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
        try:
            return media.message.get_sender().full_name
        except AttributeError:
            return ""

    def create(self, validated_data):
        message = validated_data.pop("message")
        message = ChatMessage.objects.create(**message)
        media = MessageMedia.objects.create(**validated_data, message=message)
        return media


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


class MessageWSSerializer(MessageSerializer):
    pass
