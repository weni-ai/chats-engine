from amqp.channel import Channel
from django.conf import settings
from weni.feature_flags.shortcuts import is_feature_active

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

    if not is_feature_active(
        settings.DISABLE_OLD_PROJECT_CONSUMER_FEATURE_FLAG_KEY, None, None
    ):
        channel.basic_consume("chats.projects", callback=OldProjectConsumer().handle)

    channel.basic_consume(
        "chats.update-projects", callback=ProjectUpdateConsumer().handle
    )
    channel.basic_consume(
        "chats.permissions", callback=ProjectPermissionConsumer().handle
    )
    channel.basic_consume("chats.integrated-feature", callback=SectorConsumer().handle)
    channel.basic_consume("chats.dlq", callback=DeadLetterConsumer.consume)
