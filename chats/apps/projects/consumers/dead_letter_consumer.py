import json
import logging

import amqp

from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.projects.usecases import DeadLetterHandler

LOGGER = logging.getLogger(__name__)


class DeadLetterConsumer:
    """
    This consumer is responsible for handling dead messages
    The message will be requeued if it passes the verification on the DeadLetterHandler
    else it will be rejected
    """

    @staticmethod
    def consume(message: amqp.Message):
        channel = message.channel
        try:
            notification = JSONParser.parse(message.body)

            print(
                f"[DeadLetterConsumer] - Consuming a dead message. Body: {notification}"
            )

            DeadLetterHandler(
                message=message, dead_letter_content=notification
            ).execute()

            # Will call to the default exchange
            # then use the routing key to find the queue where queue name equals routing_key
            basic_publish(
                channel=message.channel,
                content=notification,
                exchange="",
                routing_key=message.headers.get("x-first-death-queue"),
                headers=message.headers,
            )

            message.channel.basic_ack(message.delivery_tag)
        except Exception as err:
            channel.basic_reject(message.delivery_tag, requeue=False)
            print(f"[{type(err)}] {str(err)}.  response: {message.body}")
