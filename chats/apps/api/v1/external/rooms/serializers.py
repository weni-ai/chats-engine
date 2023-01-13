import json

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from chats.apps.accounts.models import User
from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactRelationsSerializer
from chats.apps.api.v1.queues.serializers import QueueSerializer
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room


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
    sector_uuid = serializers.CharField(
        required=False, write_only=True, allow_null=True
    )
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
            "is_waiting",
        ]
        read_only_fields = [
            "uuid",
            "user",
            "queue",
            "ended_at",
            "is_active",
            "transfer_history",
            "urn",
        ]
        extra_kwargs = {"queue": {"required": False, "read_only": True}}

    def create(self, validated_data):
        try:
            queue = (
                None if not validated_data.get("queue") else validated_data.pop("queue")
            )
            sector = (
                queue.sector
                if not validated_data.get("sector_uuid")
                else validated_data.pop("sector_uuid")
            )
        except AttributeError:
            raise ValidationError(
                {"detail": _("Cannot create room without queue_uuid or sector_uuid")}
            )

        if queue is None and sector is not None:
            queue = Queue.objects.filter(sector__uuid=sector).first()

        sector = queue.sector

        created_on = validated_data.get("created_on", timezone.now().time())
        if sector.is_attending(created_on) is False:
            raise ValidationError(
                {"detail": _("Contact cannot be done outside working hours")}
            )

        contact_data = validated_data.pop("contact")
        contact_external_id = contact_data.pop("external_id")
        if contact_data.get("urn"):
            validated_data["urn"] = contact_data.pop("urn").split("?")[0]
        contact, created = Contact.objects.update_or_create(
            external_id=contact_external_id, defaults=contact_data
        )

        if validated_data.get("custom_fields"):
            custom_fields = validated_data.get("custom_fields")
            if custom_fields.get("is_waiting"):
                is_waiting = custom_fields.pop("is_waiting")
                validated_data["is_waiting"] = is_waiting

        room = Room.objects.create(**validated_data, contact=contact, queue=queue)
        if room.user is None:
            available_agent = queue.available_agents.first()
            room.user = available_agent or None
            room.save()

        RoomMetrics.objects.create(room=room)

        return room
