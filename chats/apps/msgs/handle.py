from amqp.channel import Channel

from chats.apps.msgs.consumers import MsgConsumer


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume("chats.msgs", callback=MsgConsumer().handle)
