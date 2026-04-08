from django.db.models.signals import pre_delete
from django.dispatch import receiver

from chats.apps.quickmessages.models import QuickMessage


@receiver(pre_delete, sender=QuickMessage)
def log_quick_message_deletion(sender, instance, **kwargs):
    from chats.apps.projects.models import DeletionLog

    project = instance.sector.project if instance.sector else None
    DeletionLog.objects.create(
        model_name="QuickMessage",
        object_uuid=instance.pk,
        object_repr=(
            f"Shortcut: {instance.shortcut} | "
            f"Owner: {instance.user.email}"
        ),
        deleted_by=getattr(instance, "deleted_by", None),
        project=project,
    )
