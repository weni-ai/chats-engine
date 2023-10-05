from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserNameSerializer
from chats.apps.api.v1.contacts.serializers import ContactSimpleSerializer
from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.rooms.models import Room


class RoomHistorySerializer(serializers.ModelSerializer):
    user = UserNameSerializer(many=False, read_only=True)
    contact = ContactSimpleSerializer(many=False, read_only=True)
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
        ]


class RoomBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            "uuid",
            "ended_at",
        ]


class RoomDetailSerializer(serializers.ModelSerializer):
    user = UserNameSerializer(many=False, read_only=True)
    contact = ContactSimpleSerializer(many=False, read_only=True)
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
        ]
