import amqp
from django.conf import settings

from chats.apps.event_driven.backends.pyamqp_backend import basic_publish
from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.msgs.models import ChatMessageReplyIndex
from chats.apps.msgs.usecases.UpdateStatusMessageUseCase import (
    UpdateStatusMessageUseCase,
)

MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 5

update_message_usecase = UpdateStatusMessageUseCase()


def bulk_create():
    """Process all pending messages in bulk"""
    update_message_usecase._bulk_create()


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
                print("[MessageStatusConsumer] - Invalid body format")
                channel.basic_ack(message.delivery_tag)
                return
        except Exception as error:
            print(f"[MessageStatusConsumer] - JSON parse error: {error}")
            channel.basic_ack(message.delivery_tag)
            return

        if (message_id := body.get("message_id")) and (
            message_status := body.get("status")
        ):
            headers = getattr(message, "headers", None)
            if not headers or not isinstance(headers, dict):
                headers = {}
            retry_count = int(headers.get("x-retry-count", 0))

            if ChatMessageReplyIndex.objects.filter(external_id=message_id).exists():
                channel.basic_ack(message.delivery_tag)
                print(
                    f"[MessageStatusConsumer] - Consuming a message. Body: {message.body}"
                )
                try:
                    update_message_usecase.update_status_message(
                        message_id, message_status
                    )
                except Exception as error:
                    print(f"[MessageStatusConsumer] - Error processing: {error}")
            else:
                if retry_count < MAX_RETRIES:
                    new_headers = dict(headers)
                    new_headers["x-retry-count"] = retry_count + 1
                    basic_publish(
                        channel=channel,
                        content=body,
                        exchange="chats.msgs-status-delay",
                        headers=new_headers,
                    )
                channel.basic_ack(message.delivery_tag)
        else:
            channel.basic_ack(message.delivery_tag)
