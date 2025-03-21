import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.projects.usecases.update_status import UpdateStatusMessageUseCase


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

        if body.get("message_id") and body.get("message_status"):
            update_message_usecase = UpdateStatusMessageUseCase()
            update_message_usecase.update_status_message(
                body["message_id"], body["message_status"]
            )
        else:
            print(
                "[MessageStatusConsumer] - Skipping message. 'message_id' is missing or empty."
            )

        channel.basic_ack(message.delivery_tag)
