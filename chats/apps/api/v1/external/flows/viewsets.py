from rest_framework import viewsets

from chats.apps.projects.models import Flow
from chats.apps.api.v1.external.flows.serializers import FlowSerializer
from chats.apps.api.v1.external.permission import IsExternalPermission


class FlowViewSet(viewsets.ModelViewSet):
    model = Flow
    serializer_class = FlowSerializer
    permission_classes = [
        IsExternalPermission,
    ]
    lookup_field = "uuid"
