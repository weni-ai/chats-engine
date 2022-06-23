from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from chats.apps.api.v1.msgs.serializers import MessageSerializer
from chats.apps.msgs.models import Message as ChatMessage


class MessageViewset(viewsets.ModelViewSet):
    queryset = ChatMessage.objects
    serializer_class = MessageSerializer
    permission_classes = [
        IsAuthenticated,
    ]
