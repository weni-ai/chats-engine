from typing import Optional
from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserNameEmailSerializer
from chats.apps.api.v1.contacts.serializers import ContactSimpleSerializer
from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.contacts.models import Contact
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import SectorTag


def build_closed_by_payload(room: Room) -> Optional[dict]:
    """
    Build the `closed_by` payload for room history endpoints.

    The contract requires `automatic_closed` to live *inside* the closed_by
    object so the front can render the closure context (manual vs automatic)
    in a single place. When the room was closed automatically without an
    agent (typical for inactivity), we still return the object with
    null user fields and `automatic_closed=True`.

    Returns None only when neither a user nor an automatic flag is set
    (preserves the current behavior for older rooms).
    """
    user = room.closed_by
    automatic_closed = bool(getattr(room, "automatic_closed", False))

    if user is None and not automatic_closed:
        return None

    return {
        "first_name": getattr(user, "first_name", None),
        "last_name": getattr(user, "last_name", None),
        "email": getattr(user, "email", None),
        "automatic_closed": automatic_closed,
    }


class ContactOptimizedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["uuid", "name", "external_id", "email", "document"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        room = self.context.get("parent", {}).get("room")

        if room and room.protocol:
            if room.service_chat:
                data["name"] = f"{room.service_chat} | {room.protocol} | {data['name']}"
            else:
                data["name"] = f"{data['name']} | {room.protocol}"

        return data


class RoomHistorySerializer(serializers.ModelSerializer):
    user = UserNameEmailSerializer(many=False, read_only=True)
    contact = ContactOptimizedSerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    closed_by = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "uuid",
            "created_on",
            "ended_at",
            "user",
            "contact",
            "tags",
            "protocol",
            "service_chat",
            "closed_by",
        ]

    def get_tags(self, obj):
        return TagSimpleSerializer(
            # Including the (soft) deleted tags
            SectorTag.all_objects.filter(rooms__in=[obj]),
            many=True,
        ).data

    def get_closed_by(self, obj: Room) -> Optional[dict]:
        return build_closed_by_payload(obj)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        contact_serializer = ContactOptimizedSerializer(
            instance.contact, context={"parent": {"room": instance}}
        )
        data["contact"] = contact_serializer.data

        return data


class RoomBasicValuesSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    ended_at = serializers.DateTimeField()


class RoomDetailSerializer(serializers.ModelSerializer):
    user = UserNameEmailSerializer(many=False, read_only=True)
    contact = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    archived_conversation_file_url = serializers.SerializerMethodField()
    closed_by = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "uuid",
            "custom_fields",
            "urn",
            "created_on",
            "ended_at",
            "user",
            "contact",
            "tags",
            "protocol",
            "is_archived",
            "archived_conversation_file_url",
            "closed_by",
        ]

    def get_closed_by(self, obj: Room) -> Optional[dict]:
        return build_closed_by_payload(obj)

    def get_contact(self, obj):
        contact_data = ContactSimpleSerializer(obj.contact).data
        if obj.protocol:
            contact_data["name"] = f"{contact_data['name']} | {obj.protocol}"
        return contact_data

    def get_tags(self, obj):
        return TagSimpleSerializer(
            # Including the (soft) deleted tags
            SectorTag.all_objects.filter(rooms__in=[obj]),
            many=True,
        ).data

    def get_archived_conversation_file_url(self, obj: Room) -> Optional[str]:
        return obj.get_archived_conversation_file_url()
