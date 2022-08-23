from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from chats.apps.api.v1.msgs import serializers as msgs_serializers
from chats.apps.msgs.models import Message, MessageMedia

class MessageViewset(
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        GenericViewSet
):
    queryset = Message.objects.all()
    serializer_class = msgs_serializers.MessageSerializer

    def get_queryset(self):
        return super().get_queryset()

    def perform_create(self, serializer):
        serializer.save()
