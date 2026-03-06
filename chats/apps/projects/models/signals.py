from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from chats.apps.projects.models import Project, ProjectPermission
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


@receiver(pre_delete, sender=ProjectPermission)
def requeue_rooms_on_permission_delete(sender, instance, **kwargs):
    """
    When an agent is removed from a project, return their active rooms
    back to the queue so they can be reassigned.
    """
    from chats.apps.rooms.models import Room
    from chats.apps.rooms.services import requeue_agent_rooms

    rooms = Room.objects.filter(
        user=instance.user,
        queue__sector__project=instance.project,
        is_active=True,
    )
    requeue_agent_rooms(rooms)
