from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.contacts.models import Contact


class ContactViewset(viewsets.ModelViewSet):
    queryset = Contact.objects
    serializer_class = ContactSerializer
    permission_classes = [
        IsAuthenticated,
    ]
