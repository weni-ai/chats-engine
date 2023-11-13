from django.db.utils import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import APIException

from chats.apps.api.v1.accounts.serializers import UserNameEmailSerializer

from ..models import Discussion, DiscussionUser
from ..models.validators import validate_queue_and_room
from .feedbacks import create_discussion_feedback_message


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

            discussion.create_discussion_message(initial_message)
            discussion.create_discussion_user(
                from_user=created_by, to_user=created_by, role=0
            )
            feedback = {"user": created_by.first_name, "queue": discussion.queue.name}
            create_discussion_feedback_message(discussion, feedback, "cd")

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
                detail={"detail": f"{type(err)}: {err}"},
            )  # TODO: treat this error on the EXCEPTION_HANDLER instead of the serializer

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
    email = serializers.CharField(source="permission.user.email", read_only=True)

    class Meta:
        model = DiscussionUser
        fields = [
            "first_name",
            "last_name",
            "email",
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
