from amqp.channel import Channel

from .consumers import ProjectConsumer, TemplateTypeConsumer


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume("chats.template-types", callback=TemplateTypeConsumer.consume)
    channel.basic_consume("chats.projects", callback=ProjectConsumer.consume)
