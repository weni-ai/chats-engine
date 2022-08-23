from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.api.v1.queues.serializers import QueueSerializer
from chats.apps.api.v1.sectors.serializers import DetailSectorTagSerializer
from chats.apps.rooms.models import Room


class RoomSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    contact = ContactSerializer(many=False, read_only=True)
    queue = QueueSerializer(many=False, read_only=True)
    tags = DetailSectorTagSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = "__all__"
        read_only_fields = [
            "started_at",
            "ended_at",
        ]


class TransferRoomSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=False)
    queue = QueueSerializer(many=False, read_only=False)
    contact = ContactSerializer(many=False, read_only=True)
    tags = DetailSectorTagSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = "__all__"
        read_only_fields = [
            "contact",
            "ended_at",
            "is_active",
            "transfer_history",
            "tags",
        ]

        extra_kwargs = {
            "tags": {"required": False},
            "user": {"required": False, "allow_null": False},
            "queue": {"required": False, "allow_null": False},
        }
