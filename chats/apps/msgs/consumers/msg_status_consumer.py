import time

import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.msgs.tasks import process_message_status

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
                print("[MessageStatusConsumer] Empty or invalid message body")
                channel.basic_ack(message.delivery_tag)
                return
        except Exception as error:
            print(f"[MessageStatusConsumer] Failed to parse message: {error}")
            channel.basic_ack(message.delivery_tag)
            return

        if (message_id := body.get("message_id")) and (
            message_status := body.get("status")
        ):
            try:
                print(
                    f"[MessageStatusConsumer] Processing status update - ID: {message_id}, Status: {message_status}"
                )
                process_message_status.delay(message_id, message_status)
                channel.basic_ack(message.delivery_tag)
                print(
                    f"[MessageStatusConsumer] Successfully queued status update for {message_id}"
                )
            except Exception as error:
                print(f"[MessageStatusConsumer] Failed to send to Celery: {error}")
                raise
        else:
            print(
                f"[MessageStatusConsumer] Missing required fields - message_id: {body.get('message_id')}, status: {body.get('status')}"
            )
            channel.basic_ack(message.delivery_tag)
