from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from chats.apps.api.v2.quickmessages.cache import (
    invalidate_sector_quick_messages_cache,
)
from chats.apps.quickmessages.models import QuickMessage


@receiver(post_save, sender=QuickMessage)
def invalidate_cache_on_save(sender, instance, **kwargs):
    if instance.sector_id is None:
        return
    invalidate_sector_quick_messages_cache(
        sector_uuid=str(instance.sector_id),
        project_uuid=str(instance.sector.project_id),
    )


@receiver(post_delete, sender=QuickMessage)
def invalidate_cache_on_delete(sender, instance, **kwargs):
    if instance.sector_id is None:
        return
    invalidate_sector_quick_messages_cache(
        sector_uuid=str(instance.sector_id),
        project_uuid=str(instance.sector.project_id),
    )
