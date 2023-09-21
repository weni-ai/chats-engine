import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.projects.usecases import TemplateTypeCreation


class TemplateTypeConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
        consumer_name="TemplateTypeConsumer",
    )
    def consume(message: amqp.Message):
        print(f"[TemplateTypeConsumer] - Consuming a message. Body: {message.body}")
        body = JSONParser.parse(message.body)

        template_type_creation = TemplateTypeCreation(config=body)
        template_type_creation.create()

        message.channel.basic_ack(message.delivery_tag)
