from rest_framework import serializers

from chats.apps.contacts.models import Contact


class RoomsContactsInternalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["uuid", "name", "external_id"]
