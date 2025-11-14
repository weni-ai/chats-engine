import logging

from rest_framework import serializers

from chats.apps.msgs.models import ChatMessageReplyIndex
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia
from chats.apps.rooms.models import RoomNote

LOGGER = logging.getLogger(__name__)


class UserMinimalSerializer(serializers.Serializer):
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)


class ContactMinimalSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class MessageMediaSimpleSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MessageMedia
        fields = [
            "content_type",
            "message",
            "url",
            "created_on",
        ]
        read_only_fields = [
            "content_type",
            "message",
            "url",
            "created_on",
        ]

    def get_url(self, media: MessageMedia):
        return media.url


class MessageSerializerV2(serializers.ModelSerializer):
    """Serializer for the messages endpoint v2 - read-only"""

    user = UserMinimalSerializer(many=False, required=False, read_only=True)
    contact = ContactMinimalSerializer(many=False, required=False, read_only=True)
    media = MessageMediaSimpleSerializer(many=True, required=False, read_only=True)
    replied_message = serializers.SerializerMethodField(read_only=True)
    internal_note = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "uuid",
            "user",
            "contact",
            "text",
            "seen",
            "media",
            "created_on",
            "replied_message",
            "is_read",
            "is_delivered",
            "internal_note",
            "is_automatic_message",
        ]
        read_only_fields = [
            "uuid",
            "user",
            "contact",
            "text",
            "seen",
            "media",
            "created_on",
            "replied_message",
            "is_read",
            "is_delivered",
            "internal_note",
            "is_automatic_message",
        ]

    def get_replied_message(self, obj):
        if obj.metadata is None or obj.metadata == {}:
            return None

        context = obj.metadata.get("context", {})
        if not context or context == {} or "id" not in context:
            return None

        try:
            replied_id = context.get("id")
            replied_msg = ChatMessageReplyIndex.objects.get(external_id=replied_id)

            result = {
                "uuid": str(replied_msg.message.uuid),
                "text": replied_msg.message.text or "",
            }

            media_items = replied_msg.message.medias.all()
            media_data = []
            if media_items.exists():
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
                    "first_name": replied_msg.message.user.first_name,
                    "last_name": replied_msg.message.user.last_name,
                    "email": replied_msg.message.user.email,
                }

            if replied_msg.message.contact:
                result["contact"] = {
                    "uuid": str(replied_msg.message.contact.uuid),
                    "name": replied_msg.message.contact.name,
                }

            return result
        except Exception as error:
            LOGGER.error("Error getting replied message: %s", error)
            return None

    def get_internal_note(self, obj):
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
