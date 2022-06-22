from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.conf import settings

from chats.apps.contacts.models import Contact


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"
