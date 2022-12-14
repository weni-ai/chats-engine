from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactRelationsSerializer
from chats.apps.api.v1.queues.serializers import QueueSerializer
from chats.apps.api.v1.sectors.serializers import DetailSectorTagSerializer
from chats.apps.rooms.models import Room
from chats.apps.accounts.models import User
from chats.apps.queues.models import Queue


class RoomSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    contact = ContactRelationsSerializer(many=False, read_only=True)
    queue = QueueSerializer(many=False, read_only=True)
    tags = DetailSectorTagSerializer(many=True, read_only=True)
    unread_msgs = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = "__all__"
        read_only_fields = [
            "created_on",
            "ended_at",
            "custom_fields",
        ]

    def get_unread_msgs(self, room: Room):
        return room.messages.filter(seen=False).count()

    def get_last_message(self, room: Room):
        last_message = (
            room.messages.order_by("-created_on")
            .exclude(user__isnull=True, contact__isnull=True)
            .first()
        )
        return "" if last_message is None else last_message.text


class TransferRoomSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, required=False, read_only=True)
    user_email = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        required=False,
        source="user",
        slug_field="email",
        write_only=True,
        allow_null=True,
    )
    queue_uuid = serializers.PrimaryKeyRelatedField(
        queryset=Queue.objects.all(), required=False, source="queue", write_only=True
    )
    queue = QueueSerializer(many=False, required=False, read_only=True)
    contact = ContactRelationsSerializer(many=False, required=False, read_only=True)
    tags = DetailSectorTagSerializer(many=True, required=False, read_only=True)

    class Meta:
        model = Room
        exclude = ["callback_url"]
        read_only_fields = [
            "uuid",
            "user",
            "queue",
            "contact",
            "ended_at",
            "is_active",
            "custom_fields",
            "transfer_history",
            "tags",
            "ended_by",
        ]

        extra_kwargs = {
            "queue": {"required": False, "read_only": True, "allow_null": False},
            "contact": {"required": False, "read_only": True, "allow_null": False},
            "user": {"required": False, "read_only": True, "allow_null": False},
        }


class RoomContactSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    queue = QueueSerializer(many=False, read_only=True)
    tags = DetailSectorTagSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = [
            "user",
            "queue",
            "tags",
            "created_on",
            "ended_at",
            "custom_fields",
        ]
