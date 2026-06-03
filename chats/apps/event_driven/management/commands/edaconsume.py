from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string

from ...base_app import EventDrivenAPP


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

    def handle(self, *args, **options):
        params_class_path = options.get("params_class")

        if params_class_path:
            params_class = import_string(params_class_path)
            from weni.eda.django.consumers import start_consuming

            start_consuming(params_class)
            return

        EventDrivenAPP().backend.start_consuming()
