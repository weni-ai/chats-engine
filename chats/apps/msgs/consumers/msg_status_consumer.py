import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.msgs.tasks import process_message_status


class MessageStatusConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
        consumer_name="MessageStatusConsumer",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        try:
            body = JSONParser.parse(message.body)
            if not body or not isinstance(body, dict):
                channel.basic_ack(message.delivery_tag)
                return
        except Exception:
            channel.basic_ack(message.delivery_tag)
            return

        if (message_id := body.get("message_id")) and (
            message_status := body.get("status")
        ):
            try:
                process_message_status.delay(message_id, message_status)
                channel.basic_ack(message.delivery_tag)
            except Exception as error:
                print(f"[MessageStatusConsumer] Failed to send to Celery: {error}")
                raise
        else:
            channel.basic_ack(message.delivery_tag)
