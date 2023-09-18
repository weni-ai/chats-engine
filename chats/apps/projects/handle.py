from amqp.channel import Channel

from .consumers import TemplateTypeConsumer, ProjectConsumer, DeadLetterConsumer


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume(
        "chats.template-types", callback=TemplateTypeConsumer().handle
    )
    channel.basic_consume("chats.projects", callback=ProjectConsumer().handle)
    channel.basic_consume("chats.dlq", callback=DeadLetterConsumer.consume)
