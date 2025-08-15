from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chats.apps.accounts'

    def ready(self):
        # Import signals to register them
        from . import signals  # noqa
