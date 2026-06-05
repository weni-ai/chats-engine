from amqp.channel import Channel

from .consumers import (
    DeadLetterConsumer,
    OldProjectConsumer,
    ProjectPermissionConsumer,
    ProjectUpdateConsumer,
    SectorConsumer,
    TemplateTypeConsumer,
)


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume(
        "chats.template-types", callback=TemplateTypeConsumer().handle
    )

    channel.basic_consume("chats.projects", callback=OldProjectConsumer().handle)

    channel.basic_consume(
        "chats.update-projects", callback=ProjectUpdateConsumer().handle
    )
    channel.basic_consume(
        "chats.permissions", callback=ProjectPermissionConsumer().handle
    )
    channel.basic_consume("chats.integrated-feature", callback=SectorConsumer().handle)
    channel.basic_consume("chats.dlq", callback=DeadLetterConsumer.consume)
