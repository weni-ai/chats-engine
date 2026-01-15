from datetime import datetime
from typing import Optional

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from weni.feature_flags.shortcuts import is_feature_active

from chats.apps.accounts.models import User
from chats.apps.msgs.models import AutomaticMessage
from chats.apps.rooms.models import Room
from chats.apps.contacts.models import Contact
from chats.apps.sectors.models import Sector, SectorTag


SERVER_TZ = timezone.get_current_timezone()


class RoomContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "uuid",
            "name",
            "external_id",
        ]


class RoomUserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="full_name")

    class Meta:
        model = User
        fields = ["name", "email"]


class RoomTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorTag
        fields = ["uuid", "name"]
        ref_name = "V2ExternalRoomTagSerializer"


class RoomSectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["uuid", "name"]


class ExternalRoomMetricsSerializer(serializers.ModelSerializer):
    contact = RoomContactSerializer(read_only=True)
    user = RoomUserSerializer(read_only=True)
    tags = RoomTagSerializer(many=True, read_only=True)
    interaction_time = serializers.IntegerField(source="metric.interaction_time")
    automatic_message_sent_at = serializers.SerializerMethodField()
    time_to_send_automatic_message = serializers.SerializerMethodField()
    sector = RoomSectorSerializer(read_only=True, source="queue.sector")
    first_user_message_sent_at = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "uuid",
            "created_on",
            "interaction_time",
            "ended_at",
            "urn",
            "contact",
            "user",
            "user_assigned_at",
            "first_user_message_sent_at",
            "tags",
            "protocol",
            "automatic_message_sent_at",
            "first_user_assigned_at",
            "time_to_send_automatic_message",
            "sector",
            "custom_fields",
        ]

    def _is_denormalized_enabled(self, obj) -> bool:
        project = obj.queue.sector.project if obj.queue else None
        if not project:
            return False
        request = self.context.get("request")
        user_email = request.user.email if request and hasattr(request, "user") else ""
        return is_feature_active(
            settings.DENORMALIZED_MESSAGE_FIELDS_FLAG_KEY,
            user_email,
            str(project.uuid),
        )

    def get_first_user_message_sent_at(self, room: Room) -> Optional[datetime]:
        if self._is_denormalized_enabled(room):
            if room.first_agent_message_at:
                return room.first_agent_message_at.astimezone(SERVER_TZ)
            return None
        # Fallback: query original
        first_msg = (
            room.messages.filter(user__isnull=False).order_by("created_on").first()
        )
        if first_msg:
            return first_msg.created_on.astimezone(SERVER_TZ)
        return None

    def get_automatic_message_sent_at(self, obj: Room) -> Optional[datetime]:
        if self._is_denormalized_enabled(obj):
            if obj.automatic_message_sent_at:
                return obj.automatic_message_sent_at.astimezone(SERVER_TZ)
            return None
        # Fallback: query original
        automatic_message = AutomaticMessage.objects.filter(room=obj).first()
        if automatic_message:
            return automatic_message.message.created_on.astimezone(SERVER_TZ)
        return None

    def get_time_to_send_automatic_message(self, room: Room) -> Optional[int]:
        if self._is_denormalized_enabled(room):
            if room.automatic_message_sent_at and room.first_user_assigned_at:
                return max(
                    int(
                        (
                            room.automatic_message_sent_at
                            - room.first_user_assigned_at
                        ).total_seconds()
                    ),
                    0,
                )
            return None
        # Fallback: query original
        if not room.first_user_assigned_at:
            return 0
        automatic_message = AutomaticMessage.objects.filter(room=room).first()
        if automatic_message:
            return max(
                int(
                    (
                        automatic_message.message.created_on
                        - room.first_user_assigned_at
                    ).total_seconds()
                ),
                0,
            )
        return None
