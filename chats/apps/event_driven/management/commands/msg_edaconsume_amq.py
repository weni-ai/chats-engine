import os
import signal

from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string


def handle_sigterm(*args):
    """
    Handle SIGTERM signal - exit gracefully.
    """
    print("[msg_edaconsume_amq] - Received SIGTERM signal, exiting gracefully")
    os._exit(0)


class Command(BaseCommand):
    """
    Starts the Weni EDA consumer for message status events connected to the
    Amazon MQ broker over SSL (port 5671) using
    weni.eda.django.AMQConnectionParamsFactory.

    Used by the docker-entrypoint.sh `edaconsumemsg-amq` alias.
    """

    AMQ_PARAMS_CLASS = "weni.eda.django.AMQConnectionParamsFactory"

    def add_arguments(self, parser):
        parser.add_argument(
            "--group",
            dest="group",
            default="eda",
            help=(
                "Consumer group label, kept for parity with the entrypoint "
                "aliases. Currently informational only."
            ),
        )

    def handle(self, *args, **options):
        signal.signal(signal.SIGTERM, handle_sigterm)

        from django.conf import settings

        # Point the EDA consumers handler to the messages handler so this AMQ
        # process registers only message consumers on the Amazon MQ channel.
        settings.EDA_CONSUMERS_HANDLE = "chats.apps.msgs.handle.handle_consumers"

        params_class = import_string(self.AMQ_PARAMS_CLASS)

        from weni.eda.django.consumers import start_consuming

        start_consuming(params_class)
