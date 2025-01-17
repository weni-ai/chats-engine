from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers

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
    # Write
    direction = serializers.ChoiceField(
        choices=(
            ("incoming", _("incoming")),
            ("outgoing", _("outgoing")),
        ),
        write_only=True,
    )
    attachments = AttachmentSerializer(many=True, required=False, write_only=True)
    text = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=""
    )
    # Read
    media = MessageMediaSerializer(required=False, many=True, read_only=True)
    contact = ContactRelationsSerializer(many=False, required=False, read_only=True)
    user = UserSerializer(many=False, required=False, read_only=True)

    class Meta:
        model = Message
        fields = [
            "uuid",
            # Write
            "room",
            "text",
            "created_on",
            "direction",
            "attachments",
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

        return msg
