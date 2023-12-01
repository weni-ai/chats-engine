from ..app_services.feedbacks import create_discussion_feedback_message
from ..exceptions import DiscussionValidationException
from ..models import Discussion
from ..models.validators import validate_queue_and_room


class CreateDiscussionUseCase:
    def __init__(self, serialized_data: dict, created_by: object):
        self.serialized_data = serialized_data
        self.created_by = created_by

    def execute(self):
        initial_message = self.serialized_data.pop("initial_message")
        if not validate_queue_and_room(
            self.serialized_data.get("queue"), self.serialized_data.get("room")
        ):
            raise DiscussionValidationException(
                "Cannot set outside project queue on the discussion"
            )

        self.serialized_data["created_by"] = self.created_by
        discussion = Discussion.objects.create(**self.serialized_data)

        feedback = {"user": self.created_by.first_name, "queue": discussion.queue.name}
        create_discussion_feedback_message(discussion, feedback, "dc", notify=False)

        discussion.create_discussion_message(initial_message, notify=False)

        discussion.create_discussion_user(
            from_user=self.created_by, to_user=self.created_by, role=0
        )

        discussion.notify("create")

        return discussion
