from rest_framework import serializers
from timezone_field.rest_framework import TimeZoneSerializerField

from chats.apps.projects.models import LinkContact, Project


class ProjectSerializer(serializers.ModelSerializer):
    timezone = TimeZoneSerializerField(use_pytz=False)

    class Meta:
        model = Project
        fields = [
            "name",
            "date_format",
            "timezone",
        ]
        read_only_fields = [
            "timezone",
        ]


class LinkContactSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = LinkContact
        fields = ["user_email", "contact", "project"]

    def get_user_email(self, linked_contact: LinkContact) -> str:
        try:
            return linked_contact.user.email
        except AttributeError:
            return ""


class ProjectFlowContactSerializer(serializers.Serializer):
    name = serializers.CharField()
    language = serializers.CharField(required=False, max_length=3)
    urns = serializers.ListField(child=serializers.CharField(), max_length=100)
    groups = serializers.ListField(
        required=False, child=serializers.CharField(), max_length=100
    )
    fields = serializers.JSONField(
        required=False,
    )


class ProjectFlowStartSerializer(serializers.Serializer):
    groups = serializers.ListField(child=serializers.CharField(), max_length=100)
    contacts = serializers.ListField(child=serializers.CharField(), max_length=100)
    flow = serializers.CharField()
