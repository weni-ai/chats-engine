from rest_framework.response import Response
from chats.apps.api.v1.quickmessages.serializers import QuickMessageSerializer
from chats.apps.quickmessages.models import QuickMessage
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from django.utils.translation import gettext_lazy as _


class QuickMessageViewset(viewsets.ModelViewSet):
    queryset = QuickMessage.objects
    serializer_class = QuickMessageSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    def get_queryset(self, *args, **kwargs):
        return QuickMessage.objects.all().filter(user=self.request.user)
