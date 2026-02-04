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

        return super().validate(attrs)

    def create(self, validated_data):
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
