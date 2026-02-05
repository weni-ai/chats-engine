from django.core.management.base import BaseCommand


from chats.apps.csat.models import CSATFlowProjectConfig
from chats.apps.csat.flows.definitions.flow import CSAT_FLOW_VERSION


class Command(BaseCommand):
    help = "Check the versions of the CSAT flows"

    def handle(self, *args, **options):
        up_to_date_projects_count = CSATFlowProjectConfig.objects.filter(
            version=CSAT_FLOW_VERSION
        ).count()
        outdated_projects_count = CSATFlowProjectConfig.objects.filter(
            version__lt=CSAT_FLOW_VERSION
        ).count()

        self.stdout.write(
            self.style.SUCCESS(f"Up to date projects: {up_to_date_projects_count}")
        )
        self.stdout.write(
            self.style.WARNING(f"Outdated projects: {outdated_projects_count}")
        )
