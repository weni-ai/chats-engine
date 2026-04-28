from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from chats.apps.discussions.app_services.feedbacks import (
    create_discussion_feedback_message,
)
from chats.apps.discussions.exceptions import UserProjectPermissionNotFound
from chats.apps.discussions.models import Discussion

User = get_user_model()


class AddUserToDiscussionUseCase:
    def execute(self, discussion: Discussion, user_email: str, from_user) -> dict:
        user = User.objects.get(email=user_email)

        if discussion.is_added_user(user):
            raise ValidationError(
                f"User {user_email} is already added to this discussion"
            )

        try:
            added_agent = discussion.create_discussion_user(
                from_user=from_user, to_user=user
            )
        except UserProjectPermissionNotFound as e:
            raise ValidationError(e)

        feedback = {"user": added_agent.user.first_name}
        create_discussion_feedback_message(discussion, feedback, "da")

        return {
            "first_name": added_agent.user.first_name,
            "last_name": added_agent.user.last_name,
            "role": added_agent.role,
        }
