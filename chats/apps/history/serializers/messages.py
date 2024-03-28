from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserNameSerializer
from chats.apps.api.v1.contacts.serializers import ContactSimpleSerializer
from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.rooms.models import Room


class MessageReportSerializer(serializers.Serializer):
    uuid = serializers.CharField()
    room = serializers.CharField()
    user__email = serializers.CharField()
    contact__name = serializers.CharField()
    text = serializers.CharField(read_only=True)
    media__content_type = serializers.CharField()
    media__url = serializers.CharField()
    created_on = serializers.CharField()
