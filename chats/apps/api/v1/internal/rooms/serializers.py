from rest_framework import serializers
from django.utils import timezone

from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.rooms.models import Room


class RoomInternalListSerializer(serializers.ModelSerializer):
    contact = serializers.CharField(source="contact.name")
    agent = serializers.SerializerMethodField()
    tags = TagSimpleSerializer(many=True, required=False)
    sector = serializers.CharField(source="queue.sector.name")
    queue = serializers.CharField(source="queue.name")
    link = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    first_response_time = serializers.SerializerMethodField()
    waiting_time = serializers.SerializerMethodField()

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
            "link",
            "duration",
            "first_response_time",
            "waiting_time",
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
                if obj.user and obj.is_active
                else None
            ),
            "type": "internal",
        }

    def get_duration(self, obj: Room) -> int:
        if not obj.first_user_assigned_at:
            return None
        
        if obj.is_active and obj.user:
            return int((timezone.now() - obj.first_user_assigned_at).total_seconds())
        elif not obj.is_active and obj.ended_at:
            return int((obj.ended_at - obj.first_user_assigned_at).total_seconds())
        
        return None

    def get_first_response_time(self, obj: Room) -> int:
        if not obj.first_user_assigned_at:
            return None
        
        first_response_at = getattr(obj, 'first_response_at', None)
        
        if first_response_at:
            return int((first_response_at - obj.first_user_assigned_at).total_seconds())
        
        return None

    def get_waiting_time(self, obj: Room) -> int:
        if not obj.added_to_queue_at:
            return None
        
        if obj.is_active and not obj.user:
            return int((timezone.now() - obj.added_to_queue_at).total_seconds())
        elif obj.first_user_assigned_at:
            return int((obj.first_user_assigned_at - obj.added_to_queue_at).total_seconds())
        
        return None
