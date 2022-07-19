import json

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.contacts.serializers import ContactSerializer
# from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.sectors.serializers import SectorSerializer
from chats.apps.rooms.models import Room, RoomTag


class RoomTagSectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomTag
        fields = "__all__"


class RoomTagSerializer(serializers.ModelSerializer):
    sector = SectorSerializer(many=False, read_only=True)

    class Meta:
        model = RoomTag
        fields = "__all__"


class DetailRoomTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomTag
        exclude = [
            "sector",
        ]


class RoomSerializer(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=True)
    contact = ContactSerializer(many=False, read_only=True)
    sector = SectorSerializer(many=False, read_only=True)
    tags = DetailRoomTagSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = "__all__"
        read_only_fields = [
            "started_at",
            "ended_at",
        ]


class TransferRoomSerializer(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=False)
    sector = SectorSerializer(many=False, read_only=False)
    contact = ContactSerializer(many=False, read_only=True)
    tags = DetailRoomTagSerializer(many=True, read_only=True)

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
