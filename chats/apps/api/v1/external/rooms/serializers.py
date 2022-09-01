from rest_framework import serializers

from chats.apps.rooms.models import Room
from chats.apps.api.v1.rooms.serializers import TransferRoomSerializer


class RoomFlowSerializer(TransferRoomSerializer):
    sector_uuid = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = Room
        fields = [
            "uuid",
            "user",
            "queue",
            "ended_at",
            "is_active",
            "transfer_history",
            # Writable Fields
            "sector_uuid",
            "queue_uuid",
            "user_email",
            "contact",
            "created_on",
            "custom_fields",
            "callback_url",
        ]
        read_only_fields = [
            "uuid",
            "user",
            "queue",
            "ended_at",
            "is_active",
            "transfer_history",
        ]

        extra_kwargs = {field: {"required": False} for field in fields}
        extra_kwargs.update(
            {
                "queue": {"required": False, "read_only": True, "allow_null": False},
                "user": {"required": False, "read_only": True, "allow_null": False},
            }
        )
