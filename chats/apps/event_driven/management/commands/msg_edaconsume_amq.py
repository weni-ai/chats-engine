import os
import signal

from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string
from weni.eda.django.eda_app.management.commands.edaconsume import Command as WeniEDACommand


def handle_sigterm(*args):
    """
    Handle SIGTERM signal - exit gracefully.
    """
    print("[msg_edaconsume_amq] - Received SIGTERM signal, exiting gracefully")
    os._exit(0)


class Command(WeniEDACommand):
    def handle(self, *args, **options):
        super().handle(*args, **options)