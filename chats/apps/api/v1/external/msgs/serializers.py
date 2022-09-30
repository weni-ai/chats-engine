from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, exceptions

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactRelationsSerializer
from chats.apps.msgs.models import Message, MessageMedia

from chats.apps.api.v1.msgs.serializers import MessageMediaSerializer


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.URLField(source="media_url")

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
            "created_on",
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

        msg = super().create(validated_data)
        media_list = [MessageMedia(**media_data, message=msg) for media_data in medias]
        medias = MessageMedia.objects.bulk_create(media_list)
        return msg
