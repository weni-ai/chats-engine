from rest_framework import serializers

from chats.apps.api.v1.msgs.serializers import process_uploaded_media_file
from chats.apps.msgs.models import MessageMedia


class MessageMediaCreateSerializerV2(serializers.ModelSerializer):
    """
    Upload media for a room before attaching it to a message.
    """

    url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MessageMedia
        fields = [
            "uuid",
            "room",
            "content_type",
            "media_file",
            "url",
            "created_on",
        ]
        read_only_fields = ["uuid", "url", "created_on"]
        extra_kwargs = {
            "media_file": {"write_only": True, "required": True},
            "room": {"required": True},
            "content_type": {"required": False},
        }

    def get_url(self, media: MessageMedia):
        return media.public_url

    def create(self, validated_data):
        validated_data = process_uploaded_media_file(validated_data)
        validated_data["message"] = None
        return super().create(validated_data)
