from django.apps import AppConfig


class ContactsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chats.apps.contacts"

    def ready(self):
        import chats.apps.contacts.signals