from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chats.apps.dashboard"

    def ready(self):
        from . import signals  # noqa: F401
