import logging

from django.conf import settings

from chats.apps.projects.usecases.exceptions import (
    InvalidDLQHeaders,
    ReceivedErrorMessage,
)

LOGGER = logging.getLogger(__name__)

REJECT_REASON = ["rejected", "delivery_limit"]
REQUEUE_REASON = ["expired", "maxlen"]


class DeadLetterHandler:
    """
    This handler is responsible for verifying if the message can be requeued.
    """

    def __init__(self, message, dead_letter_content: dict) -> None:
        self.dead_letter_content = dead_letter_content
        self.message = message

    def execute(self):
        if self.dead_letter_content.get("error_type"):
            log_message = (
                f"[{self.dead_letter_content.get('error_type')}] "
                + f"Error message: {self.dead_letter_content.get('error_message')}. "
                + f"Body: {self.dead_letter_content.get('original_message')}"
            )
            raise ReceivedErrorMessage(log_message)
        msg_headers = self.message.headers
        x_death_header = msg_headers.get("x-death")

        if not x_death_header:
            raise InvalidDLQHeaders("[X] no 'x-death' header on the message found!")

        msg_info_header = x_death_header[0]
        if msg_info_header.get("reason") in REJECT_REASON:
            raise InvalidDLQHeaders(
                f"[X] {msg_info_header.get('reason')} dead messages cannot be requeued!"
            )
        if msg_info_header.get("count") >= settings.EDA_REQUEUE_LIMIT:
            raise InvalidDLQHeaders(
                f"[X] Dead messages cannot be requeued more than {settings.EDA_REQUEUE_LIMIT} times!"
            )
