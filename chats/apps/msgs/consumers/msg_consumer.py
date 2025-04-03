import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.msgs.usecases.set_msg_external_id import SetMsgExternalIdUseCase


class MsgConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        # routing_key="whatsapp-cloud-token",
        consumer_name="MsgConsumer",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        print(f"[MsgConsumer] - Consuming a message. Body: {message.body}")
        # body = JSONParser.parse(message.body)

        # if body.get("message_id"):
        #     set_msg_external_id_usecase = SetMsgExternalIdUseCase()
        #     set_msg_external_id_usecase.execute(
        #         body["message_id"], body["external_id"]
        #     )
        # else:
        #     print(
        #         "[MsgConsumer] - Skipping message. 'message_id' is missing or empty."
        #     )

        channel.basic_ack(message.delivery_tag)
