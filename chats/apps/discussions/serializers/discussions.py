from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserNameEmailSerializer

from ..models import Discussion


class DiscussionCreateSerializer(serializers.ModelSerializer):
    initial_message = serializers.CharField(
        required=True, write_only=True, allow_null=True
    )

    class Meta:
        model = Discussion
        fields = ["uuid", "room", "queue", "subject", "initial_message"]


class DiscussionListSerializer(serializers.ModelSerializer):
    contact = serializers.CharField(source="room.contact.name", read_only=True)

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


class DiscussionWSSerializer(DiscussionListSerializer):
    added_agents = serializers.SerializerMethodField()

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
            "added_agents",
        ]

    def get_added_agents(self, discussion: Discussion):
        agents = discussion.added_users.values_list("permission__user", flat=True)
        return list(agents)


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
