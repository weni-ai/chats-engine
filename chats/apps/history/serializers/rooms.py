from typing import Optional
from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserNameEmailSerializer
from chats.apps.api.v1.contacts.serializers import ContactSimpleSerializer
from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.contacts.models import Contact
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import SectorTag


class ClosedBySerializer(serializers.Serializer):
    """
    Serializes the closure context for a room (the agent who closed it, plus
    whether the closure was automatic). The `automatic_closed` flag lives
    inside this payload so the front can render manual vs automatic closure
    from a single object.
    """

    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    automatic_closed = serializers.SerializerMethodField()

    def get_first_name(self, room: Room) -> Optional[str]:
        return getattr(room.closed_by, "first_name", None)

    def get_last_name(self, room: Room) -> Optional[str]:
        return getattr(room.closed_by, "last_name", None)

    def get_email(self, room: Room) -> Optional[str]:
        return getattr(room.closed_by, "email", None)

    def get_automatic_closed(self, room: Room) -> bool:
        return bool(getattr(room, "automatic_closed", False))


def _serialize_closed_by(room: Room) -> Optional[dict]:
    """
    Returns the serialized `closed_by` payload, or None when the room has
    neither a closing agent nor the automatic flag set (preserves the legacy
    behavior for older rooms).
    """
    if room.closed_by is None and not getattr(room, "automatic_closed", False):
        return None
    return ClosedBySerializer(room).data


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
        return _serialize_closed_by(obj)

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
        return _serialize_closed_by(obj)

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
