from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.conf import settings

from chats.apps.msgs.models import Message as ChatMessage


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = "__all__"
