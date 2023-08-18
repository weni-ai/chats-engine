import logging

import amqp

from chats.apps.event_driven.parsers import JSONParser
from chats.apps.projects.usecases import DeadLetterHandler

LOGGER = logging.getLogger(__name__)


class DeadLetterConsumer:
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
            # TODO Requeue the messages and maintain the x-death headers
            # the count is very important, so it does not become an infinite loop.
            # The requeueing can be done on RabbitMQ, but it need to be validated
            # my initial idea is to configure a ttl(or do a reject/nack on the message here), the x-dead-letter-exchange and pass the queue as router_key.
            # But, for now(untill the requeue logic is implemented, here or in the RabbitMQ configs), we'll log the data and ack the message

            message.channel.basic_ack(message.delivery_tag)
        except Exception as err:
            channel.basic_reject(message.delivery_tag, requeue=False)
            LOGGER.debug(
                f"[{type(err)}] Failed to process dead message.  response: {message.body}"
            )
