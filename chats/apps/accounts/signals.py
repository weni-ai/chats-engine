from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from chats.apps.accounts.models import User
from chats.core.cache_utils import invalidate_user_email_cache


@receiver(pre_save, sender=User)
def capture_old_email(sender, instance, **kwargs):
    """
    Capture the old email before saving to invalidate it if changed
    """
    if instance.pk:
        try:
            old_instance = User.objects.only("email").get(pk=instance.pk)
            instance._old_email = old_instance.email
        except User.DoesNotExist:
            instance._old_email = None
    else:
        instance._old_email = None


@receiver(post_save, sender=User)
def invalidate_user_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate cache when user email is updated
    """
    if created:
        return

    old_email = getattr(instance, "_old_email", None)
    if old_email and old_email != instance.email:
        invalidate_user_email_cache(old_email)
        invalidate_user_email_cache(instance.email)


@receiver(post_delete, sender=User)
def invalidate_user_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate cache when user is deleted
    """
    invalidate_user_email_cache(instance.email)
