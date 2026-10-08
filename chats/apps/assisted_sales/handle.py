from amqp.channel import Channel

from chats.apps.assisted_sales.consumers import WwcChannelConsumer


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume("chats.wwc-channel", callback=WwcChannelConsumer().handle)
