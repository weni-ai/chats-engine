from django.apps import AppConfig


class QueuesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chats.apps.queues"

    def ready(self):
        import chats.apps.queues.signals
