from rest_framework import serializers

from chats.apps.msgs.models import Message
from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact


class ArchiveUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "name",
        ]


class ArchiveContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "name",
            "external_id",
        ]


class ArchiveMessageSerializer(serializers.ModelSerializer):
    user = ArchiveUserSerializer(read_only=True)
    contact = ArchiveContactSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            "uuid",
            "text",
            "created_on",
            "user",
            "contact",
        ]
