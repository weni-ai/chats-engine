from django.db.models.signals import pre_delete
from django.dispatch import receiver

from chats.apps.queues.models import QueueAuthorization


@receiver(pre_delete, sender=QueueAuthorization)
def log_queue_authorization_deletion(sender, instance, **kwargs):
    from chats.apps.projects.models import DeletionLog

    DeletionLog.objects.create(
        model_name="QueueAuthorization",
        object_uuid=instance.pk,
        object_repr=(
            f"Queue: {instance.queue.name} | "
            f"Agent: {instance.permission.user.email}"
        ),
        deleted_by=getattr(instance, "deleted_by", None),
        project=instance.project,
    )
