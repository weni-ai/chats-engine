from rest_framework import serializers

from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.rooms.models import Room


class RoomInternalListSerializer(serializers.ModelSerializer):
    contact = serializers.CharField(source="contact.name")
    agent = serializers.SerializerMethodField()
    tags = TagSimpleSerializer(many=True, required=False)
    sector = serializers.CharField(source="queue.sector.name")
    queue = serializers.CharField(source="queue.name")
    link = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "uuid",
            "agent",
            "contact",
            "urn",
            "is_active",
            "ended_at",
            "sector",
            "queue",
            "created_on",
            "tags",
        ]

    def get_agent(self, obj):
        try:
            return obj.user.full_name
        except AttributeError:
            return ""

    def get_link(self, obj: Room) -> dict:
        return {
            "url": (
                f"chats:dashboard/view-mode/{obj.user.email}/?room_uuid={obj.uuid}"
                if obj.user
                else None
            )
        }
