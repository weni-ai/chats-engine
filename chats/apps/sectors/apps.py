from django.apps import AppConfig


class SectorsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chats.apps.sectors"

    def ready(self):
        # Import signals to ensure they are registered
        from chats.apps.projects.models import permission_signals  # noqa: F401