from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.conf import settings

from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.rooms.models import Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"

    old_messages = serializers.SerializerMethodField()

    def get_old_messages(self, obj):
        other_rooms = self.contact.rooms.all()
        messages = ChatMessage.objects.filter(room__in=other_rooms)[
            : settings.OLD_MESSAGES_LIMIT
        ]
        return messages
