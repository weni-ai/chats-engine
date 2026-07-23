import io
import logging

import magic
from django.conf import settings
from django.db import transaction
from pydub import AudioSegment
from rest_framework import exceptions, serializers

from chats.apps.api.core.serializers import CommaSeparatedListField
from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.msgs.choices import BulkMessageSendRoomStatus
from chats.apps.msgs.models import (
    BulkMessageSend,
    BulkMessageSendMessage,
    BulkMessageSendMessageStatus,
    ChatMessageReplyIndex,
)
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia
from chats.apps.msgs.utils import extract_wamid_core, is_reply_core_fallback_active
from chats.apps.ai_features.improve_user_message.choices import (
    ImprovedUserMessageStatusChoices,
    ImprovedUserMessageTypeChoices,
)
from chats.apps.rooms.models import RoomNote
from chats.apps.ai_features.improve_user_message.tasks import (
    register_message_improvement_task,
)

LOGGER = logging.getLogger(__name__)

BULK_SEND_ROOM_STATUS_CHOICES = ("waiting", "ongoing")


class BulkSendRoomsCountQueryParamsSerializer(serializers.Serializer):
    project = serializers.UUIDField(required=True)
    status = CommaSeparatedListField(
        child=serializers.ChoiceField(choices=BULK_SEND_ROOM_STATUS_CHOICES),
        required=True,
        allow_empty=False,
    )
    queues = CommaSeparatedListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        default=list,
    )
    agents = CommaSeparatedListField(
        child=serializers.EmailField(),
        required=False,
        allow_empty=True,
        default=list,
    )


class BulkSendMessagesSerializer(serializers.Serializer):
    text = serializers.CharField(required=True, allow_blank=False)
    status = serializers.ListField(
        child=serializers.ChoiceField(choices=BulkMessageSendRoomStatus.choices),
        required=True,
        allow_empty=False,
    )
    project = serializers.UUIDField(required=True)
    queues = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        allow_null=True,
        default=list,
    )
    agents = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        allow_empty=True,
        allow_null=True,
        default=list,
    )


class BulkSendRecentHistorySerializer(serializers.ModelSerializer):
    sent_at = serializers.DateTimeField(source="created_on", read_only=True)

    class Meta:
        model = BulkMessageSend
        fields = ["uuid", "text", "sent_at"]


class BulkSendHistoryQueryParamsSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    sender = serializers.EmailField(required=False)
    status = serializers.ChoiceField(
        choices=BulkMessageSendMessageStatus.choices,
        required=False,
    )


class BulkSendHistorySerializer(serializers.ModelSerializer):
    contact = serializers.SerializerMethodField()
    queue = serializers.SerializerMethodField()
    sent_by = serializers.SerializerMethodField()
    date = serializers.DateTimeField(
        source="created_on", format="%Y-%m-%d", read_only=True
    )

    class Meta:
        model = BulkMessageSendMessage
        fields = ["contact", "queue", "sent_by", "date", "status"]

    def get_contact(self, obj: BulkMessageSendMessage) -> dict:
        contact = obj.room.contact
        return {"name": contact.name if contact else None}

    def get_queue(self, obj: BulkMessageSendMessage) -> dict:
        queue = obj.room.queue
        return {"name": queue.name if queue else None}

    def get_sent_by(self, obj: BulkMessageSendMessage) -> dict:
        return {"name": obj.bulk_message_send.user.name}


def _resolve_reply_index(message: ChatMessage, replied_id: str):
    """Resolve a :class:`ChatMessageReplyIndex` for a replied-to WAMID.

    Performs an exact ``external_id`` lookup first. When the feature flag is
    active for the message's project, falls back to matching the stable
    WAMID core (``external_id_core``) so replies still mount when Meta sends
    a different envelope (``HBgM`` vs ``HBgT``) inside ``context.id``.

    The fallback is scoped to ``message.room_id`` to prevent a core
    collision between rooms/projects from surfacing a foreign message.
    """

    exact_match = ChatMessageReplyIndex.objects.filter(external_id=replied_id).first()
    if exact_match is not None:
        return exact_match

    core = extract_wamid_core(replied_id)
    if not core:
        return None

    try:
        project_uuid = str(message.room.project_uuid or "") or str(message.project.uuid)
    except Exception:
        project_uuid = ""

    if not is_reply_core_fallback_active(project_uuid):
        return None

    return (
        ChatMessageReplyIndex.objects.filter(
            external_id_core=core,
            message__room_id=message.room_id,
        )
        .order_by("-created_on")
        .first()
    )


"""
TODO: Refactor these serializers into less classes
"""


class MessageMediaSimpleSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)
    transcription = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MessageMedia
        fields = [
            "content_type",
            "message",
            "media_file",
            "url",
            "created_on",
            "transcription",
        ]
        ref_name = "V1MessageMediaSimpleSerializer"
        extra_kwargs = {
            "media_file": {"write_only": True},
            "message": {"read_only": True, "required": False},
        }

    def get_url(self, media: MessageMedia):
        return media.public_url

    def get_sender(self, media: MessageMedia):
        try:
            return media.message.get_sender().full_name
        except AttributeError:
            return ""

    def get_transcription(self, media: MessageMedia):
        """
        Get transcription data for audio media.
        Returns text and feedback for the current user.
        """
        try:
            transcription = media.transcription
        except Exception:
            return None

        if not transcription or transcription.status != "DONE":
            return None

        result = {"text": transcription.text}

        # Get user feedback if available
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            feedback = transcription.feedbacks.filter(user=request.user).first()
            if feedback:
                result["feedback"] = {"liked": feedback.liked}
            else:
                result["feedback"] = {"liked": None}
        else:
            result["feedback"] = {"liked": None}

        return result


class MessageMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)
    sender = serializers.SerializerMethodField(read_only=True)
    transcription = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MessageMedia
        fields = [
            "sender",
            "content_type",
            "message",
            "media_file",
            "url",
            "created_on",
            "transcription",
        ]

        extra_kwargs = {
            "media_file": {"write_only": True},
        }

    def get_url(self, media: MessageMedia):
        return media.public_url

    def get_sender(self, media: MessageMedia):
        try:
            return media.message.get_sender().full_name
        except AttributeError:
            return ""

    def get_transcription(self, media: MessageMedia):
        """
        Get transcription data for audio media.
        Returns text and feedback for the current user.
        """
        try:
            transcription = media.transcription
        except Exception:
            return None

        if not transcription or transcription.status != "DONE":
            return None

        result = {"text": transcription.text}

        # Get user feedback if available
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            feedback = transcription.feedbacks.filter(user=request.user).first()
            if feedback:
                result["feedback"] = {"liked": feedback.liked}
            else:
                result["feedback"] = {"liked": None}
        else:
            result["feedback"] = {"liked": None}

        return result

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
        return media.public_url

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


class AITextImprovementSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ImprovedUserMessageStatusChoices.choices)
    type = serializers.ChoiceField(choices=ImprovedUserMessageTypeChoices.choices)


class MessageSerializer(BaseMessageSerializer):
    """Serializer for the messages endpoint"""

    media = MessageMediaSimpleSerializer(many=True, required=False)
    replied_message = serializers.SerializerMethodField(read_only=True)
    internal_note = serializers.SerializerMethodField(read_only=True)
    ai_text_improvement = AITextImprovementSerializer(
        write_only=True, required=False, allow_null=True
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
            "media",
            "created_on",
            "metadata",
            "replied_message",
            "is_read",
            "is_delivered",
            "internal_note",
            "is_automatic_message",
            "automatic_message_type",
            "ai_text_improvement",
        ]
        read_only_fields = [
            "uuid",
            "user",
            "created_on",
            "contact",
        ]

    def create(self, validated_data):
        ai_text_improvement = validated_data.pop("ai_text_improvement", None)
        msg = super().create(validated_data)

        if ai_text_improvement:
            transaction.on_commit(
                lambda message_uuid=str(msg.uuid), improvement_type=ai_text_improvement[
                    "type"
                ], status=ai_text_improvement["status"]: (
                    register_message_improvement_task.delay(
                        message_uuid=message_uuid,
                        improvement_type=improvement_type,
                        status=status,
                    )
                )
            )

        return msg

    def get_replied_message(self, obj):
        if obj.metadata is None or obj.metadata == {}:
            return None

        context = obj.metadata.get("context", {})
        if not context or context == {} or "id" not in context:
            return None

        try:
            replied_id = context.get("id")
            replied_msg = _resolve_reply_index(obj, replied_id)
            if replied_msg is None:
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
            "media": [
                {"content_type": media.content_type, "url": media.url}
                for media in note.medias.all()
            ],
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
