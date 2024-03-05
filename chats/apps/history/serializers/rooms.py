from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserNameSerializer
from chats.apps.api.v1.contacts.serializers import ContactSimpleSerializer
from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.rooms.models import Room


class RoomHistorySerializer(serializers.ModelSerializer):
    user = UserNameSerializer(many=False, read_only=True)
    contact = serializers.SerializerMethodField()
    tags = TagSimpleSerializer(many=True, read_only=True)
    protocol = serializers.SerializerMethodField()

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
        ]

    def get_contact(self, obj):
        contact_data = ContactSimpleSerializer(obj.contact).data
        if obj.protocol:
            contact_data["name"] = f"{contact_data['name']} | {obj.protocol}"
        return contact_data

    def get_protocol(self, obj):
        return obj.protocol


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
    protocol = serializers.SerializerMethodField()

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

    def get_protocol(self, obj):
        return obj.protocol
