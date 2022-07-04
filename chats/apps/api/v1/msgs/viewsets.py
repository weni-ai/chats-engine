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

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_room("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_room("update")

    def perform_destroy(self, instance):
        instance.notify_room("destroy")
        super().perform_destroy(instance)
