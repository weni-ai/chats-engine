from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.msgs.models import Message, MessageMedia


class AttachmentSerializer(serializers.ListSerializer):
    content_type = serializers.CharField()
    url = serializers.URLField()


class MsgFlowSerializer(serializers.ModelSerializer):
    # Write
    direction = serializers.ChoiceField(
        choices=(
            ("incoming", _("incoming")),
            ("outgoing", _("outgoing")),
        )
    )
    attachments = AttachmentSerializer()

    # Read
    media = serializers.FileField(required=False, many=True)
    contact = ContactSerializer(many=False, required=False, read_only=True)
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
            "created_at",
            "contact",
        ]


class MessageMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageMedia
        fields = "__all__"
