from django.core.management.base import BaseCommand
from rest_framework import status


from chats.apps.csat.models import CSATFlowProjectConfig
from chats.apps.csat.flows.definitions.flow import (
    CSAT_FLOW_DEFINITION_DATA,
    CSAT_FLOW_VERSION,
)
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient


class Command(BaseCommand):
    help = "Update flows"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Update all project configs that have a version lower than the current version",
        )
        parser.add_argument(
            "--project-uuid",
            type=str,
            help="Update flow for a specific project UUID",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        current_version = CSAT_FLOW_VERSION

        # Validate arguments
        if not options["all"] and not options["project_uuid"]:
            self.stdout.write(
                self.style.ERROR("You must specify either --all or --project-uuid")
            )
            return

        # Build query based on options
        if options["project_uuid"]:
            projects_configs = CSATFlowProjectConfig.objects.filter(
                project__uuid=options["project_uuid"]
            )
            if not projects_configs.exists():
                self.stdout.write(
                    self.style.ERROR(
                        f"No project config found for UUID: {options['project_uuid']}"
                    )
                )
                return
        else:  # --all option
            projects_configs = CSATFlowProjectConfig.objects.filter(
                version__lt=current_version
            )

        self.stdout.write(
            self.style.INFO(
                f"Found {projects_configs.count()} projects configs to update"
            )
        )

        if projects_configs.count() == 0:
            self.stdout.write(
                self.style.INFO("There are no projects configs to update")
            )
            return

        # Dry run mode
        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
            for project_config in projects_configs:
                self.stdout.write(
                    self.style.INFO(
                        f"Would update project config {project_config.project.name} ({project_config.project.uuid})"
                    )
                )
            return

        flows_client = FlowRESTClient()

        for project_config in projects_configs:
            self.stdout.write(
                self.style.INFO(
                    f"Updating project config {project_config.project.name} ({project_config.project.uuid})"
                )
            )

            response = flows_client.create_or_update_flow(
                project_config.project,
                CSAT_FLOW_DEFINITION_DATA,
            )

            if not status.is_success(response.status_code):
                self.stdout.write(
                    self.style.ERROR(
                        (
                            "Failed to update flow for project "
                            f"{project_config.project.name} "
                            f"({project_config.project.uuid})"
                        )
                    )
                )
                continue

            results = response.json().get("results", [])
            if not results:
                self.stdout.write(
                    self.style.ERROR(
                        f"No results found for project {project_config.project.name} ({project_config.project.uuid})"
                    )
                )
                continue

            flow_uuid = results[0].get("uuid")

            project_config.flow_uuid = flow_uuid
            project_config.version = current_version
            project_config.save(update_fields=["flow_uuid", "version"])

            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated flow for project {project_config.project.name} ({project_config.project.uuid})"
                )
            )

        self.stdout.write(self.style.SUCCESS("All flows updated"))
