import json

from django.db.utils import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import APIException

from chats.apps.api.v1.accounts.serializers import UserNameEmailSerializer

from ..models import Discussion
from ..models.validators import validate_queue_and_room


def create_feedback_json(method: str, content: dict):
    return {"method": method, "content": content}


def create_discussion_feedback_message(discussion: object, feedback: dict, method: str):
    return discussion.create_discussion_message(
        message=json.dumps(create_feedback_json(method=method, content=feedback)),
        system=True,
    )


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
        if not validate_queue_and_room(
            validated_data.get("queue"), validated_data.get("room")
        ):
            APIException.status_code = 400
            raise APIException(
                detail={"detail": "Cannot set outside project queue on the discussion"},
            )

        created_by = self.context.get("user")
        validated_data["created_by"] = created_by
        try:
            discussion = super().create(validated_data)
            discussion.notify("create")

            feedback = {"user": created_by.first_name, "queue": discussion.queue.name}
            create_discussion_feedback_message(discussion, feedback, "dc")
            discussion.create_discussion_message(initial_message)
            discussion.create_discussion_user(
                from_user=created_by, to_user=created_by, role=0
            )

        except IntegrityError:
            APIException.status_code = 409
            raise APIException(
                detail={
                    "detail": "The room already have an open discussion.",
                },
            )
        except Exception as err:
            APIException.status_code = 400

            raise APIException(
                detail={"detail": f"{type(err)}: {err}111"},
            )  # TODO: treat this error on the EXCEPTION_HANDLER instead of the serializer

        return discussion


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
