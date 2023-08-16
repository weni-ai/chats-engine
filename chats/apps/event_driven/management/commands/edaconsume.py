from django.core.management.base import BaseCommand

from ...base_app import EventDrivenAPP


class Command(BaseCommand):
    def handle(self, *args, **options):
        EventDrivenAPP().backend.start_consuming()
