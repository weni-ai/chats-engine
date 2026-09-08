import logging

import amqp
from django.conf import settings

from chats.apps.assisted_sales.usecases import UpdateCopilotWwcChannelUseCase
from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser

logger = logging.getLogger(__name__)


def _body_value(body: dict, *keys):
    for key in keys:
        value = body.get(key)
        if value not in (None, ""):
            return value
    return None


class WwcChannelConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=getattr(
            settings, "CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE", "connect.dlx.topic"
        ),
        routing_key="",
        consumer_name="WwcChannelConsumer",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        print(f"[WwcChannelConsumer] - Consuming a message. Body: {message.body}")
        body = JSONParser.parse(message.body)

        if not isinstance(body, dict):
            logger.warning(
                "[WwcChannelConsumer] skipping message: invalid body",
                extra={"body_type": type(body).__name__},
            )
            channel.basic_ack(message.delivery_tag)
            return

        channel_uuid = _body_value(body, "channel_uuid", "channelUuid")
        project_uuid = _body_value(body, "project_uuid", "projectUuid")
        sector_uuid = _body_value(body, "sector_uuid", "sectorUuid")

        logger.info(
            "[WwcChannelConsumer] consuming message",
            extra={
                "channel_uuid": channel_uuid,
                "project_uuid": project_uuid,
                "sector_uuid": sector_uuid,
            },
        )

        if not channel_uuid or not project_uuid:
            logger.warning(
                "[WwcChannelConsumer] skipping message: missing channel_uuid or project_uuid",
                extra={
                    "channel_uuid": channel_uuid,
                    "project_uuid": project_uuid,
                    "body_keys": sorted(body.keys()),
                },
            )
            channel.basic_ack(message.delivery_tag)
            return

        UpdateCopilotWwcChannelUseCase().execute(
            channel_uuid=channel_uuid,
            project_uuid=project_uuid,
            sector_uuid=sector_uuid,
        )
        channel.basic_ack(message.delivery_tag)
