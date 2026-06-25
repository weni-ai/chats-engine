import os
import signal

from weni.eda.django.eda_app.management.commands.edaconsume import Command as WeniEDACommand


AMQ_PARAMS_CLASS = "weni.eda.django.connection_params.AMQConnectionParamsFactory"


def handle_sigterm(*args):
    """
    Handle SIGTERM signal - exit gracefully.
    """
    print("[msg_edaconsume_amq] - Received SIGTERM signal, exiting gracefully")
    os._exit(0)


class Command(WeniEDACommand):
    def handle(self, *args, **options):
        signal.signal(signal.SIGTERM, handle_sigterm)
        options["params_class"] = AMQ_PARAMS_CLASS
        super().handle(*args, **options)
