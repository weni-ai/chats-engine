from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, permissions, mixins, viewsets, pagination
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.contacts.models import Contact


class ContactViewset(viewsets.ModelViewSet):
    queryset = Contact.objects
    serializer_class = ContactSerializer
