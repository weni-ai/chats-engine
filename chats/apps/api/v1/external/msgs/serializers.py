from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers

from chats.apps.api.utils import create_reply_index
from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactRelationsSerializer
from chats.apps.api.v1.msgs.serializers import MessageMediaSerializer
from chats.apps.msgs.models import Message, MessageMedia


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source="media_url")

    class Meta:
        model = MessageMedia
        fields = [
            "content_type",
            "url",
        ]


class MsgFlowSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and retrieving messages via external API.

    Supports both incoming (from contact) and outgoing (to contact) messages,
    with optional attachments and metadata.
    """

    # Write
    direction = serializers.ChoiceField(
        choices=(
            ("incoming", _("incoming")),
            ("outgoing", _("outgoing")),
        ),
        write_only=True,
        help_text="Message direction: 'incoming' (from contact) or 'outgoing' (to contact)",
    )
    attachments = AttachmentSerializer(
        many=True,
        required=False,
        write_only=True,
        help_text="List of media attachments for the message",
    )
    text = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        default="",
        help_text="Message text content",
    )
    external_id = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="External message ID from the source system",
    )
    metadata = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="Additional metadata as JSON object",
    )
    # Read
    media = MessageMediaSerializer(required=False, many=True, read_only=True)
    contact = ContactRelationsSerializer(many=False, required=False, read_only=True)
    user = UserSerializer(many=False, required=False, read_only=True)
    created_on = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Message creation timestamp (ISO 8601 format)",
    )

    class Meta:
        model = Message
        fields = [
            "uuid",
            # Write
            "room",
            "text",
            "direction",
            "attachments",
            "created_on",
            "external_id",
            "metadata",
            # Read
            "user",
            "contact",
            "seen",
            "media",
        ]
        read_only_fields = [
            "uuid",
            "user",
            "contact",
            "media",
        ]

    def validate(self, attrs: dict):
        if "created_on" in attrs and attrs["created_on"] is None:
            # defaults to current time and date
            attrs.pop("created_on")
            
        print("Validated data:", attrs)  # Isso vai mostrar os dados validados no console
        if 'metadata' in attrs:
            print("Metadata found:", attrs['metadata'])
        else:
            print("Metadata not found in attrs!")
        return super().validate(attrs)

    def to_internal_value(self, data):
        print("\n\n===== RAW REQUEST DATA =====")
        print("Raw data type:", type(data))
        print("Raw data:", data)
        if 'metadata' in data:
            print("Raw metadata type:", type(data['metadata']))
            print("Raw metadata:", data['metadata'])
        else:
            print("Metadata not found in raw data!")
        print("===== END RAW REQUEST DATA =====\n\n")
        
        result = super().to_internal_value(data)
        
        print("\n\n===== AFTER to_internal_value =====")
        print("Result:", result)
        if 'metadata' in result:
            print("Metadata in result:", result['metadata'])
        else:
            print("Metadata not found in result!")
        print("===== END AFTER to_internal_value =====\n\n")
        
        return result

    def create(self, validated_data):
        # Adicione este log no início do método
        print("\n\n===== CREATE METHOD DATA =====")
        print("validated_data:", validated_data)
        if 'metadata' in validated_data:
            print("Metadata found in create:", validated_data['metadata'])
        else:
            print("Metadata not found in create!")
        print("===== END CREATE METHOD DATA =====\n\n")
        
        direction = validated_data.pop("direction")
        medias = validated_data.pop("attachments")
        room = validated_data.get("room")
        text = validated_data.get("text")

        if text is None and medias == []:
            raise exceptions.APIException(
                detail="Cannot create message without text or media"
            )
        if direction == "incoming":
            validated_data["contact"] = room.contact

        is_waiting = room.get_is_waiting()
        was_24h_valid = room.is_24h_valid
        msg = super().create(validated_data)
        media_list = [MessageMedia(**media_data, message=msg) for media_data in medias]
        medias = MessageMedia.objects.bulk_create(media_list)

        if direction == "incoming":
            validated_data["contact"] = room.contact
            if is_waiting:
                room.is_waiting = False
                room.save()
                room.notify_room("update")
            elif not was_24h_valid:
                room.notify_room("update")

        create_reply_index(msg)
        return msg


class RoomHistoryQuerySerializer(serializers.Serializer):
    """Validates query params for the external room history endpoint."""

    room = serializers.UUIDField(
        required=True,
        help_text="UUID of the room whose message history will be returned",
    )


class RoomHistoryUserSerializer(serializers.Serializer):
    """Minimal user payload used inside the room history response."""

    name = serializers.SerializerMethodField()
    email = serializers.EmailField(read_only=True)

    def get_name(self, user) -> str:
        first_name = getattr(user, "first_name", "") or ""
        last_name = getattr(user, "last_name", "") or ""
        full_name = f"{first_name} {last_name}".strip()
        return full_name or (getattr(user, "email", "") or "")


class RoomHistoryContactSerializer(serializers.Serializer):
    """Minimal contact payload used inside the room history response."""

    uuid = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class RoomHistoryMessageMediaSerializer(serializers.ModelSerializer):
    """Read-only media payload returned inside the room history response."""

    url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MessageMedia
        fields = ["content_type", "url", "created_on"]
        read_only_fields = ["content_type", "url", "created_on"]
        ref_name = "ExternalRoomHistoryMessageMediaSerializer"

    def get_url(self, media: MessageMedia) -> str:
        return media.public_url


class RoomHistoryMessageSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for messages of a closed room exposed via the
    external room history endpoint.
    """

    user = RoomHistoryUserSerializer(read_only=True, allow_null=True)
    contact = RoomHistoryContactSerializer(read_only=True, allow_null=True)
    media = RoomHistoryMessageMediaSerializer(
        many=True, read_only=True, source="medias"
    )
    replied_message = serializers.SerializerMethodField(read_only=True)
    is_automatic_message = serializers.BooleanField(read_only=True)

    class Meta:
        model = Message
        fields = [
            "uuid",
            "text",
            "user",
            "contact",
            "created_on",
            "replied_message",
            "media",
            "is_automatic_message",
        ]
        read_only_fields = fields
        ref_name = "ExternalRoomHistoryMessageSerializer"

    def get_replied_message(self, obj: Message):
        metadata = obj.metadata or {}
        context = metadata.get("context") if isinstance(metadata, dict) else None
        if not context or not isinstance(context, dict):
            return None

        replied_id = context.get("id")
        if not replied_id:
            return None

        reply_index_map = self.context.get("reply_index_map")
        if reply_index_map is None:
            return None

        reply_index = reply_index_map.get(replied_id)
        if reply_index is None:
            return None

        return {
            "uuid": str(reply_index.message.uuid),
            "text": reply_index.message.text or "",
        }
