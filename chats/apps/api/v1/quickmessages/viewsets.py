from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from chats.apps.api.v1.quickmessages.serializers import QuickMessageSerializer
from chats.apps.quickmessages.models import QuickMessage


class QuickMessageViewset(viewsets.ModelViewSet):
    queryset = QuickMessage.objects
    serializer_class = QuickMessageSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    def get_queryset(self, *args, **kwargs):
        try:
            return self.queryset.all().filter(user=self.request.user)
        except (TypeError, AttributeError):
            return self.queryset.none()
