from amqp.channel import Channel
from django.conf import settings

from .consumers import (
    DeadLetterConsumer,
    OldProjectConsumer,
    ProjectPermissionConsumer,
    ProjectUpdateConsumer,
    SectorConsumer,
    TemplateTypeConsumer,
    WeniEDAProjectConsumer,
)


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume(
        "chats.template-types", callback=TemplateTypeConsumer().handle
    )

    if settings.USE_WENI_EDA_FOR_PROJECTS:
        # TODO: Remove this checking once we permanently migrate to Weni EDA
        channel.basic_consume(
            "chats.projects", callback=WeniEDAProjectConsumer().handle
        )
    else:
        channel.basic_consume("chats.projects", callback=OldProjectConsumer().handle)

    channel.basic_consume(
        "chats.update-projects", callback=ProjectUpdateConsumer().handle
    )
    channel.basic_consume(
        "chats.permissions", callback=ProjectPermissionConsumer().handle
    )
    channel.basic_consume("chats.integrated-feature", callback=SectorConsumer().handle)
    channel.basic_consume("chats.dlq", callback=DeadLetterConsumer.consume)
