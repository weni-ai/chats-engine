from amqp.channel import Channel

from .consumers import DeadLetterConsumer, ProjectConsumer, TemplateTypeConsumer


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume("chats.template-types", callback=TemplateTypeConsumer.consume)
    channel.basic_consume("chats.projects", callback=ProjectConsumer.consume)
    channel.basic_consume("chats.dlq", callback=DeadLetterConsumer.consume)
