from django.apps import AppConfig


class SectorsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chats.apps.sectors"

    def ready(self):
        import chats.apps.sectors.signals  # noqa: F401
