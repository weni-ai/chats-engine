from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.rooms.tasks import requeue_agent_rooms_task
from chats.core.cache_utils import invalidate_project_cache


@receiver(post_save, sender=Project)
def invalidate_project_cache_on_save(sender, instance, **kwargs):
    """
    Invalidate cache when project is updated
    """
    invalidate_project_cache(str(instance.uuid))


@receiver(post_delete, sender=Project)
def invalidate_project_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate cache when project is deleted
    """
    invalidate_project_cache(str(instance.uuid))


@receiver(pre_save, sender=ProjectPermission)
def requeue_rooms_on_permission_delete(sender, instance, **kwargs):
    """
    When an agent is removed from a project, return their active rooms
    back to the queue so they can be reassigned.
    """
    try:
        old = ProjectPermission.all_objects.get(pk=instance.pk)
    except ProjectPermission.DoesNotExist:
        return

    if not old.is_deleted and instance.is_deleted:
        requeue_agent_rooms_task.delay(
            str(instance.user.email),
            str(instance.project.uuid),
        )
