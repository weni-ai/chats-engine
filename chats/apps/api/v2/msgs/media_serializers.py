from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.msgs.serializers import process_uploaded_media_file
from chats.apps.msgs.models import MessageMedia
from chats.apps.rooms.models import Room


class MessageMediaCreateSerializerV2(serializers.ModelSerializer):
    """
    Upload media for a room before attaching it to a message.
    """

    room = serializers.UUIDField(write_only=True, required=True)
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
            "content_type": {"required": False},
        }

    def get_url(self, media: MessageMedia):
        return media.public_url

    def validate_room(self, room_uuid):
        room = Room.objects.filter(uuid=room_uuid).first()
        if room is None:
            raise serializers.ValidationError(_("Room not found"))
        if room.is_active is False:
            raise serializers.ValidationError(_("Closed rooms can't receive messages"))
        return room_uuid

    def create(self, validated_data):
        with transaction.atomic():
            validated_data.pop("room", None)
            validated_data = process_uploaded_media_file(validated_data)
            validated_data["message"] = None
            return super().create(validated_data)
