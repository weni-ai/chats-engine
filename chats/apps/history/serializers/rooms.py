from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserNameSerializer
from chats.apps.api.v1.contacts.serializers import ContactSimpleSerializer
from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.contacts.models import Contact
from chats.apps.rooms.models import Room


class ContactOptimizedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["uuid", "name", "external_id"]

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
    user = UserNameSerializer(many=False, read_only=True)
    contact = ContactOptimizedSerializer(read_only=True)
    tags = TagSimpleSerializer(many=True, read_only=True)

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
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        contact_serializer = ContactOptimizedSerializer(
            instance.contact, context={"parent": {"room": instance}}
        )
        data["contact"] = contact_serializer.data

        return data


class RoomBasicValuesSerializer(serializers.Serializer):
    """
    Serializer otimizado para trabalhar com values() - performance máxima
    """

    uuid = serializers.UUIDField()
    ended_at = serializers.DateTimeField()


class RoomBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            "uuid",
            "ended_at",
        ]


class RoomDetailSerializer(serializers.ModelSerializer):
    user = UserNameSerializer(many=False, read_only=True)
    contact = serializers.SerializerMethodField()
    tags = TagSimpleSerializer(many=True, read_only=True)

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
        ]

    def get_contact(self, obj):
        contact_data = ContactSimpleSerializer(obj.contact).data
        if obj.protocol:
            contact_data["name"] = f"{contact_data['name']} | {obj.protocol}"
        return contact_data
