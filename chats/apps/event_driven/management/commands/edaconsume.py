import os
import signal

from weni.eda.django.eda_app.management.commands.edaconsume import Command as WeniEDACommand


def handle_sigterm(*args):
    """
    Handle SIGTERM signal - exit gracefully.
    """
    print("[edaconsume] - Received SIGTERM signal, exiting gracefully")
    os._exit(0)


class Command(WeniEDACommand):
    def handle(self, *args, **options):
        signal.signal(signal.SIGTERM, handle_sigterm)
        super().handle(*args, **options)
