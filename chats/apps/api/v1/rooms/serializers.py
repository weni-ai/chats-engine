import json

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.msgs.serializers import MessageSerializer
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.rooms.models import Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"
        read_only_fields = [
            "old_messages",
            "started_at",
            "ended_at",
        ]

    old_messages = serializers.SerializerMethodField()

    def get_old_messages(self, obj):
        try:
            other_rooms = obj.contact.rooms.all()
            messages = ChatMessage.objects.filter(room__in=other_rooms)[
                : settings.OLD_MESSAGES_LIMIT
            ]
            return MessageSerializer(messages, many=True).data
        except AttributeError:
            return {}
