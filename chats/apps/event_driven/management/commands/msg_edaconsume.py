import os
import signal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string

from chats.apps.msgs.handle import handle_consumers


def handle_sigterm(*args):
    """
    Handle SIGTERM signal - exit gracefully
    """
    print("[MessageStatusConsumer] - Received SIGTERM signal, exiting gracefully")
    os._exit(0)


class Command(BaseCommand):
    def handle(self, *args, **options):
        signal.signal(signal.SIGTERM, handle_sigterm)

        connection_backend = import_string(settings.EDA_CONNECTION_BACKEND)
        connection_params = dict(
            host=settings.EDA_BROKER_HOST,
            port=settings.EDA_BROKER_PORT,
            userid=settings.EDA_BROKER_USER,
            password=settings.EDA_BROKER_PASSWORD,
            virtual_host=settings.EDA_VIRTUAL_HOST,
        )
        backend = connection_backend(handle_consumers, connection_params)
        backend.start_consuming()
