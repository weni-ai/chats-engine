from django.core.exceptions import PermissionDenied

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from chats.apps.api.v1.quickmessages.serializers import QuickMessageSerializer
from chats.apps.quickmessages.models import QuickMessage


class QuickMessageViewset(viewsets.ModelViewSet):
    queryset = QuickMessage.objects.all()
    serializer_class = QuickMessageSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        if self.get_object().user == request.user:
            return super().update(request, *args, **kwargs)
        raise PermissionDenied

    def destroy(self, request, *args, **kwargs):
        if self.get_object().user == request.user:
            return super().destroy(request, *args, **kwargs)
        raise PermissionDenied

    def retrieve(self, request, *args, **kwargs):
        if self.get_object().user == request.user:
            return super().retrieve(request, *args, **kwargs)
        raise PermissionDenied

    def get_queryset(self, *args, **kwargs):
        return QuickMessage.objects.all().filter(user=self.request.user)
