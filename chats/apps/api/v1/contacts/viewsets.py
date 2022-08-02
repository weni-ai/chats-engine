from rest_framework import viewsets

from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.contacts.models import Contact


class ContactViewset(
    viewsets.GenericViewSet,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    # TODO: Include `chats.apps.api.v1.permissions.SectorAnyPermission` in permission_classes list
    permission_classes = []
