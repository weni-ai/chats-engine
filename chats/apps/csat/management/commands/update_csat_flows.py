from django.core.management.base import BaseCommand

from chats.apps.csat.tasks import update_all_projects_csat_flow_definition


class Command(BaseCommand):
    help = "Update CSAT flow definitions asynchronously for all projects"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                "Calling update_all_projects_csat_flow_definition asybc task"
            )
        )
        update_all_projects_csat_flow_definition.delay()
        self.stdout.write(
            self.style.SUCCESS(
                "update_all_projects_csat_flow_definition async task called"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "This does not mean the flows have been updated yet, "
                "just that the task has been scheduled"
            )
        )
