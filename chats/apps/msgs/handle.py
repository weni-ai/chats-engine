from amqp.channel import Channel

from chats.apps.msgs.consumers import MessageStatusConsumer, MsgConsumer


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume("chats.msgs", callback=MsgConsumer().handle)
    channel.basic_consume("chats.msgs-status", callback=MessageStatusConsumer().handle)
