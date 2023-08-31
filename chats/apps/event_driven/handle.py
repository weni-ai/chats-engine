from amqp.channel import Channel

from chats.apps.projects.handle import handle_consumers as project_handle_consumers


def handle_consumers(channel: Channel) -> None:
    pass
    project_handle_consumers(channel)
