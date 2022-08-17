from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from chats.apps.api.v1.intenal.permissions import ModuleHasPermission
from chats.apps.api.v1.sectors.serializers import SectorAuthorizationSerializer
from chats.apps.sectors.models import SectorAuthorization


class SectorAuthorizationViewset(viewsets.ModelViewSet):
    queryset = SectorAuthorization.objects.all()
    serializer_class = SectorAuthorizationSerializer
    permission_classes = [IsAuthenticated, ModuleHasPermission]
    lookup_field = "uuid"

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_user("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_user("update")

    def perform_destroy(self, instance):
        instance.notify_user("destroy")
        super().perform_destroy(instance)
