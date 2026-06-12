from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from chats.apps.api.v2.quickmessages.cache import (
    invalidate_personal_quick_messages_cache,
)
from chats.apps.quickmessages.models import QuickMessage


@receiver(post_save, sender=QuickMessage)
def invalidate_cache_on_save(sender, instance, **kwargs):
    if instance.sector_id is not None:
        return
    invalidate_personal_quick_messages_cache(instance.user.id)


@receiver(post_delete, sender=QuickMessage)
def invalidate_cache_on_delete(sender, instance, **kwargs):
    if instance.sector_id is not None:
        return

    invalidate_personal_quick_messages_cache(instance.user.id)
