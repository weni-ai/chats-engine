import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import pyamqp_call_dlx_when_error
from chats.apps.event_driven.consumers import EDAConsumer
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.projects.usecases import TemplateTypeCreation

from chats.apps.projects.models import Project
from chats.apps.projects.usecases import InvalidProjectData


class TemplateTypeConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
    )
    def consume(message: amqp.Message):
        print(f"[TemplateTypeConsumer] - Consuming a message. Body: {message.body}")
        body = JSONParser.parse(message.body)

        try:
            Project.objects.get(uuid=body.get("project_uuid"))
        except Exception as err:
            raise InvalidProjectData(err)

        template_type_creation = TemplateTypeCreation(config=body)
        template_type_creation.create()

        message.channel.basic_ack(message.delivery_tag)
