from amqp.channel import Channel

from chats.apps.projects.handle import handle_consumers as projects_handle_consumers
from chats.apps.msgs.handle import handle_consumers as msgs_handle_consumers


def handle_consumers(channel: Channel) -> None:
    projects_handle_consumers(channel)
    msgs_handle_consumers(channel)
