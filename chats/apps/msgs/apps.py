from django.apps import AppConfig


class MessagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chats.apps.msgs"

    def ready(self):
        import chats.apps.msgs.signals  # noqa
