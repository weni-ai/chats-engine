from chats.apps.projects.models import UnifiedSacMigration


class GetLatestUnifiedSacMigrationUseCase:
    """Return the latest Unified SAC migration for an organization."""

    def execute(self, org):
        if not org:
            return None
        return (
            UnifiedSacMigration.objects.filter(org=org)
            .only("uuid", "status", "error", "started_at", "finished_at")
            .order_by("-created_on")
            .first()
        )
