import os
import signal

from django.core.management.base import BaseCommand

from chats.apps.msgs.consumers.msg_status_consumer import bulk_create

from ...base_app import EventDrivenAPP


def handle_sigterm(*args):
    """
    Handle SIGTERM signal by flushing any pending messages
    before exiting.
    """
    print(
        "[MessageStatusConsumer] - Received SIGTERM signal, flushing buffers before exit"
    )
    bulk_create()
    print("[MessageStatusConsumer] - Buffers flushed, exiting")
    os._exit(0)


class Command(BaseCommand):
    def handle(self, *args, **options):
        signal.signal(signal.SIGTERM, handle_sigterm)
        EventDrivenAPP().backend.start_consuming()
