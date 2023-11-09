from ..models import DiscussionMessage


class CreateMessageWithMediaUseCase:
    def __init__(self, discussion, user, msg_content: dict, notify: bool = True):
        self.discussion = discussion
        self.user = user
        self.msg_content = msg_content
        self.notify = notify

    def _create_message(self, text):
        return DiscussionMessage.objects.create(
            discussion=self.discussion, user=self.user, text=text
        )

    def execute(self):
        text = self.msg_content.pop("text")
        msg = self._create_message(text)
        media = msg.medias.create(**self.msg_content)
        if self.notify:
            msg.notify("create")
        return media
