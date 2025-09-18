from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chats.apps.projects"

    def ready(self):
        from .models import signals  # noqa: F401
