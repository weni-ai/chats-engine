import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.msgs.usecases.UpdateStatusMessageUseCase import (
    UpdateStatusMessageUseCase,
)


class MessageStatusConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
        consumer_name="MessageStatusConsumer",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        print(f"[MessageStatusConsumer] - Consuming a message. Body: {message.body}")
        body = JSONParser.parse(message.body)

        if (message_id := body.get("message_id")) and (
            message_status := body.get("status")
        ):
            if message_status == "read":
                return

            update_message_usecase = UpdateStatusMessageUseCase()
            update_message_usecase.update_status_message(message_id, message_status)
        else:
            print(
                "[MessageStatusConsumer] - Skipping message. 'message_id' and/or 'message_status' is missing or empty."
            )

        channel.basic_ack(message.delivery_tag)
