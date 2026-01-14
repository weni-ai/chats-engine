import io
import logging

import magic
from django.conf import settings
from pydub import AudioSegment
from rest_framework import exceptions, serializers

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.msgs.models import ChatMessageReplyIndex
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia
from chats.apps.rooms.models import RoomNote

LOGGER = logging.getLogger(__name__)

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
        ref_name = "V1MessageMediaSimpleSerializer"
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
        if file_type in settings.FILE_CHECK_CONTENT_TYPE:
            file_type = media.name[-3:]
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
    user_email = serializers.EmailField(
        write_only=True, required=False, allow_null=True
    )
    text = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=""
    )
    metadata = serializers.JSONField(required=False, allow_null=True)

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
            "metadata",
        ]
        read_only_fields = [
            "uuid",
            "user",
            "created_on",
            "contact",
        ]

    def validate(self, attrs):
        email = attrs.pop("user_email", None)
        if email:
            from chats.core.cache_utils import get_user_id_by_email_cached

            uid = get_user_id_by_email_cached(email)
            if uid is None:
                raise serializers.ValidationError({"user_email": "not found"})
            attrs["user_id"] = email.lower()
        return super().validate(attrs)

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
    replied_message = serializers.SerializerMethodField(read_only=True)
    internal_note = serializers.SerializerMethodField(read_only=True)

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
            "metadata",
            "replied_message",
            "is_read",
            "is_delivered",
            "internal_note",
            "is_automatic_message",
            "internal_note",
        ]
        read_only_fields = [
            "uuid",
            "user",
            "created_on",
            "contact",
        ]

    def get_replied_message(self, obj):
        if obj.metadata is None or obj.metadata == {}:
            return None

        context = obj.metadata.get("context", {})
        if not context or context == {} or "id" not in context:
            return None

        try:
            replied_id = context.get("id")
            try:
                replied_msg = ChatMessageReplyIndex.objects.get(external_id=replied_id)
                print("replied_msg", replied_msg.message.uuid)
                print("replied_msg", replied_msg.message.text)
            except ChatMessageReplyIndex.DoesNotExist:
                return None

            result = {
                "uuid": str(replied_msg.message.uuid),
                "text": replied_msg.message.text or "",
            }
            media_items = replied_msg.message.medias.all()
            if media_items.exists():
                media_data = []
                for media in media_items:
                    media_data.append(
                        {
                            "content_type": media.content_type,
                            "message": str(media.message.uuid),
                            "url": media.url,
                            "created_on": media.created_on,
                        }
                    )
                result["media"] = media_data

            if replied_msg.message.user:
                result["user"] = {
                    "uuid": str(replied_msg.message.user.pk),
                    "name": replied_msg.message.user.full_name,
                }

            if replied_msg.message.contact:
                result["contact"] = {
                    "uuid": str(replied_msg.message.contact.uuid),
                    "name": replied_msg.message.contact.name,
                }

            return result
        except ChatMessage.DoesNotExist:
            return None

    def get_internal_note(self, obj):
        # Returns the internal note attached to this message (if any)
        try:
            note = obj.internal_note
        except RoomNote.DoesNotExist:
            return None
        except AttributeError:
            return None

        if not note:
            return None

        return {
            "uuid": str(note.uuid),
            "text": note.text,
            "is_deletable": note.is_deletable,
        }


class MessageWSSerializer(MessageSerializer):
    pass


class ChatCompletionSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField(read_only=True)
    content = serializers.CharField(read_only=True, source="text")

    class Meta:
        model = ChatMessage
        fields = [
            "role",
            "content",
        ]

        extra_kwargs = {
            "media_file": {"write_only": True},
        }

    def get_role(self, message: ChatMessage):
        if message.contact:
            return "user"
        else:
            return "assistant"
