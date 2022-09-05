from rest_framework import serializers

from chats.apps.api.v1.sectors.serializers import SectorTagSerializer
from chats.apps.contacts.models import Contact


class ContactSerializer(serializers.ModelSerializer):

    tags = SectorTagSerializer(many=True)
    agent = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            "uuid",
            "name",
            "email",
            "status",
            "custom_fields",
            "tags",
            "agent",
            "created_on",
        ]
        read_only_fields = [
            "uuid",
        ]

    def get_tags(self, contact: Contact):
        return contact.tags

    def get_agent(self, contact: Contact):
        return contact.last_agent_name


class ContactRelationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "uuid",
            "external_id",
            "name",
            "email",
            "status",
            "phone",
            "custom_fields",
            "created_on",
        ]
        read_only_fields = [
            "uuid",
        ]


class ContactWSSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"
