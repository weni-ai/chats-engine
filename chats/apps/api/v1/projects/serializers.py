from rest_framework import serializers
from timezone_field.rest_framework import TimeZoneSerializerField

from chats.apps.projects.models import (
    FlowStart,
    LinkContact,
    Project,
    ProjectPermission,
)
from chats.apps.sectors.models import Sector


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
    groups = serializers.ListField(
        required=False, child=serializers.CharField(), max_length=100
    )
    contacts = serializers.ListField(
        required=False, child=serializers.CharField(), max_length=100
    )
    flow = serializers.CharField()
    room = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default="",
        trim_whitespace=True,
    )
    params = serializers.JSONField(required=False)
    contact_name = serializers.CharField()


class ListFlowStartSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = FlowStart
        fields = ["contact_data", "name", "user", "created_on", "room"]

    def get_user(self, flow_start: FlowStart) -> str:
        try:
            return flow_start.permission.user.full_name
        except AttributeError:
            return ""


class SectorDiscussionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["uuid", "name"]


class ListProjectUsersSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.CharField(source="user.email")

    class Meta:
        model = ProjectPermission
        fields = ["first_name", "last_name", "email"]
