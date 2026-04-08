from django.db.models.signals import pre_delete
from django.dispatch import receiver

from chats.apps.queues.models import QueueAuthorization
from chats.core.middleware import get_current_user


@receiver(pre_delete, sender=QueueAuthorization)
def log_queue_authorization_deletion(sender, instance, **kwargs):
    from chats.apps.projects.models import DeletionLog

    user = get_current_user()
    DeletionLog.objects.create(
        model_name="QueueAuthorization",
        object_uuid=instance.pk,
        object_repr=(
            f"Queue: {instance.queue.name} | "
            f"Agent: {instance.permission.user.email}"
        ),
        deleted_by=user if user and not getattr(user, "is_anonymous", True) else None,
        project=instance.project,
    )
