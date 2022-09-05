from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactRelationsSerializer
from chats.apps.api.v1.queues.serializers import QueueSerializer
from chats.apps.api.v1.sectors.serializers import DetailSectorTagSerializer
from chats.apps.rooms.models import Room
from chats.apps.accounts.models import User
from chats.apps.queues.models import Queue
from chats.apps.contacts.models import Contact


class RoomFlowSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, required=False, read_only=True)
    user_email = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        required=False,
        source="user",
        slug_field="email",
        write_only=True,
        allow_null=True,
    )
    sector_uuid = serializers.CharField(required=False, write_only=True)
    queue_uuid = serializers.PrimaryKeyRelatedField(
        queryset=Queue.objects.all(), required=False, source="queue", write_only=True
    )
    queue = QueueSerializer(many=False, required=False, read_only=True)
    contact = ContactRelationsSerializer(many=False, required=False, read_only=False)

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

    def create(self, validated_data):
        contact_data = validated_data.pop("contact")
        contact_external_id = contact_data.pop("external_id")
        contact, created = Contact.objects.update_or_create(
            external_id=contact_external_id, defaults=contact_data
        )
        queue = validated_data.pop("queue")

        room = Room.objects.create(**validated_data, contact=contact, queue=queue)
        return room
