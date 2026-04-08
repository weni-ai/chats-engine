from django.db.models.signals import pre_delete
from django.dispatch import receiver

from chats.apps.quickmessages.models import QuickMessage
from chats.core.middleware import get_current_user


@receiver(pre_delete, sender=QuickMessage)
def log_quick_message_deletion(sender, instance, **kwargs):
    from chats.apps.projects.models import DeletionLog

    user = get_current_user()
    project = instance.sector.project if instance.sector else None
    DeletionLog.objects.create(
        model_name="QuickMessage",
        object_uuid=instance.pk,
        object_repr=(
            f"Shortcut: {instance.shortcut} | "
            f"Owner: {instance.user.email}"
        ),
        deleted_by=user if user and not getattr(user, "is_anonymous", True) else None,
        project=project,
    )
