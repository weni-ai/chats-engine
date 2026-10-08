import logging

import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.msgs.usecases.set_msg_external_id import SetMsgExternalIdUseCase

logger = logging.getLogger(__name__)


class MsgConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="whatsapp-cloud-token",
        consumer_name="MsgConsumer",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        print(f"[MsgConsumer] - Consuming a message. Body: {message.body}")
        body = JSONParser.parse(message.body)

        chats_uuid = body.get("chats_uuid")
        message_id = body.get("message_id")

        # Bug #1 observability: structured log shadowing the print above so
        # we get searchable fields (chats_uuid, message_id) in Sentry/Loki
        # without losing the legacy stdout line that already exists in
        # dashboards.
        logger.info(
            "[MsgConsumer] consuming message",
            extra={
                "chats_uuid": chats_uuid,
                "message_id": message_id,
                "has_chats_uuid": bool(chats_uuid),
                "has_message_id": bool(message_id),
            },
        )

        if chats_uuid and message_id:
            set_msg_external_id_usecase = SetMsgExternalIdUseCase()
            set_msg_external_id_usecase.execute(chats_uuid, message_id)
        else:
            print(
                "[MsgConsumer] - Skipping message. 'chats_uuid' or 'message_id' is missing or empty."
            )
            # Bug #1 observability: same skip information, but at WARNING
            # level and with the missing keys as ``extra`` so we can alert
            # and group on it. The print above is intentionally preserved
            # so existing Loki queries keep matching.
            logger.warning(
                "[MsgConsumer] skipping message: missing chats_uuid or message_id",
                extra={
                    "chats_uuid": chats_uuid,
                    "message_id": message_id,
                    "body_keys": sorted(body.keys())
                    if isinstance(body, dict)
                    else [],
                },
            )

        channel.basic_ack(message.delivery_tag)
