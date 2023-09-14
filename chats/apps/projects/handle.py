from amqp.channel import Channel

from .consumers import TemplateTypeConsumer


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume("chats.template-types", callback=TemplateTypeConsumer.handle)
