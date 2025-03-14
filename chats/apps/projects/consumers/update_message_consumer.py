import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.projects.usecases.update_external_id import (
    UpdateExternalIdMessageUseCase,
)


class MessageConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
        consumer_name="MessageConsumer",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        print(f"[MessageConsumer] - Consuming a message. Body: {message.body}")
        body = JSONParser.parse(message.body)

        update_message_usecase = UpdateExternalIdMessageUseCase()
        update_message_usecase.update_external_id(
            body["chatsUUID"], body["message_id"]
        )

        channel.basic_ack(message.delivery_tag)
