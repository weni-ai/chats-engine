"""
Consumer handlers for the Amazon MQ broker (weni-eda).

This handler is intentionally separate from the legacy
`chats.apps.projects.handle.handle_consumers` so the AMQ-only process started
by the `edaconsume-amq` entrypoint alias does not try to bind to queues that
only exist on the legacy RabbitMQ broker.

Only consumers that have been migrated to the new broker should be registered
here.
"""

from amqp.channel import Channel
from django.conf import settings

from chats.apps.projects.consumers import WeniEDAProjectConsumer


def handle_amq_consumers(channel: Channel) -> None:
    queue_name = getattr(
        settings, "PROJECT_AMQ_QUEUE_NAME", "chats.projects.queue"
    )
    channel.basic_consume(
        queue_name, callback=WeniEDAProjectConsumer().handle
    )
