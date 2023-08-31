import amqp

from chats.apps.event_driven.parsers import JSONParser
from chats.apps.projects.usecases import TemplateTypeHandler


# TODO: use commented code, it's commented because we need to test only the create method and other modules don't follow this message structure
class TemplateTypeConsumer:
    @staticmethod
    def consume(message: amqp.Message):
        notification = JSONParser.parse(message.body)

        print(f"[TemplateTypeConsumer] - Consuming a message. Body: {notification}")
        content = notification  # notification.get("content")

        TemplateTypeHandler(
            "create",  # action=notification.get("action"),
            config=content,
        ).execute()

        message.channel.basic_ack(message.delivery_tag)
