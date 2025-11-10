from datetime import datetime
from typing import Optional
from django.utils import timezone
from rest_framework import serializers

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

    def get_first_user_message_sent_at(self, room: Room) -> Optional[datetime]:
        if (
            first_msg := room.messages.filter(user__isnull=False)
            .order_by("created_on")
            .first()
        ):
            return first_msg.created_on.astimezone(SERVER_TZ)

        return None

    def get_automatic_message_sent_at(self, obj: Room) -> Optional[datetime]:
        automatic_message: AutomaticMessage = AutomaticMessage.objects.filter(
            room=obj
        ).first()

        if automatic_message:
            return automatic_message.message.created_on.astimezone(SERVER_TZ)

        return None

    def get_time_to_send_automatic_message(self, room: Room) -> Optional[int]:
        automatic_message: AutomaticMessage = AutomaticMessage.objects.filter(
            room=room
        ).first()

        if automatic_message and room.first_user_assigned_at:
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
