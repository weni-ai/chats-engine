import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.projects.usecases.sector_creation import SectorCreationUseCase


class SectorConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
        consumer_name="SectorConsumer",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        print(f"[SectorConsumer] - Consuming a message. Body: {message.body}")

        body = JSONParser.parse(message.body)

        sector_dtos = SectorCreationUseCase.create_sector_dto(body)

        # SectorCreationUseCase.create(sector_dtos)

        channel.basic_ack(message.delivery_tag)
