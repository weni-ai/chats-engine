import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.projects.usecases import TemplateTypeHandler


# TODO: use commented code, it's commented because we need to test only the
# create method and other modules don't follow this message structure
class TemplateTypeConsumer:
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
    )
    def consume(message: amqp.Message):
        print(f"[TemplateTypeConsumer] - Consuming a message. Body: {message.body}")
        notification = JSONParser.parse(message.body)

        content = notification  # notification.get("content")

        TemplateTypeHandler(
            "create",  # action=notification.get("action"),
            config=content,
        ).execute()

        message.channel.basic_ack(message.delivery_tag)
