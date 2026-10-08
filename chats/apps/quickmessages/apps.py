from django.apps import AppConfig


class QuickMessagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chats.apps.quickmessages"

    def ready(self):
        import chats.apps.api.v2.quickmessages.signals  # noqa: F401
