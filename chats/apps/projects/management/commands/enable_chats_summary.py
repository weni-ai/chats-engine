from django.core.management.base import BaseCommand

from chats.apps.projects.models import Project


class Command(BaseCommand):
    help = "Enable is_chats_summary_enabled for a project by UUID"

    def add_arguments(self, parser):
        parser.add_argument("uuid", type=str)

    def handle(self, *args, **options):
        uuid = options["uuid"]
        updated = Project.objects.filter(uuid=uuid).update(
            is_chats_summary_enabled=True
        )

        if updated:
            self.stdout.write(
                self.style.SUCCESS(f"Project {uuid}: is_chats_summary_enabled=True")
            )
        else:
            self.stdout.write(self.style.ERROR(f"Project {uuid} not found"))
