from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chats.apps.rooms"

    def ready(self):
        import chats.apps.rooms.signals