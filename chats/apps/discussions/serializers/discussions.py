from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserNameEmailSerializer

from ..models import Discussion, DiscussionUser


class DiscussionCreateSerializer(serializers.ModelSerializer):
    initial_message = serializers.CharField(
        required=True, write_only=True, allow_null=True
    )

    class Meta:
        model = Discussion
        fields = ["uuid", "room", "queue", "subject", "initial_message"]
        read_only_fields = [
            "uuid",
        ]

    def create(self, validated_data):
        initial_message = validated_data.pop("initial_message")
        created_by = self.context.get("user")
        validated_data["created_by"] = created_by

        discussion = super().create(validated_data)
        discussion.notify("create")

        discussion.create_discussion_message(initial_message)
        discussion.create_discussion_user(user=created_by, role=0)

        return discussion


class DiscussionListSerializer(serializers.ModelSerializer):
    contact = serializers.CharField(source="room.contact.name", read_only=True)
    created_by = serializers.CharField(source="created_by.first_name", read_only=True)

    class Meta:
        model = Discussion
        fields = [
            "uuid",
            "subject",
            "created_by",
            "contact",
            "created_on",
            "is_active",
            "is_queued",
        ]


class DiscussionUserListSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        source="permission.user.first_name", read_only=True
    )
    last_name = serializers.CharField(
        source="permission.user.last_name", read_only=True
    )

    class Meta:
        model = DiscussionUser
        fields = [
            "first_name",
            "last_name",
            "role",
        ]


class DiscussionDetailSerializer(serializers.ModelSerializer):
    contact = serializers.CharField(source="room.contact.name", read_only=True)
    created_by = UserNameEmailSerializer(many=False, required=False, read_only=True)

    class Meta:
        model = Discussion
        fields = [
            "uuid",
            "created_by",
            "room",
            "contact",
            "created_on",
        ]
