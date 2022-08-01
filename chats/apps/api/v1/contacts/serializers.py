from rest_framework import serializers

from chats.apps.contacts.models import Contact


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"


class ContactWSSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"
