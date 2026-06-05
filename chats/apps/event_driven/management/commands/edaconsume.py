import os
import signal

from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string

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
    def add_arguments(self, parser):
        parser.add_argument(
            "--params-class",
            dest="params_class",
            default=None,
            help=(
                "Dotted path to a ConnectionParamsFactory (e.g. "
                "'weni.eda.django.AMQConnectionParamsFactory') to connect over "
                "SSL on port 5671. If omitted, uses the default broker."
            ),
        )
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

        params_class_path = options.get("params_class")

        if params_class_path:
            params_class = import_string(params_class_path)
            from weni.eda.django.consumers import start_consuming

            start_consuming(params_class)
            return

        EventDrivenAPP().backend.start_consuming()
