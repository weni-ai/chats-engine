from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from chats.apps.projects.models import Project
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
