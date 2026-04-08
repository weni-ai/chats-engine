from django.db.models.signals import pre_delete
from django.dispatch import receiver

from chats.apps.sectors.models import SectorAuthorization
from chats.core.middleware import get_current_user


@receiver(pre_delete, sender=SectorAuthorization)
def log_sector_authorization_deletion(sender, instance, **kwargs):
    from chats.apps.projects.models import DeletionLog

    user = get_current_user()
    DeletionLog.objects.create(
        model_name="SectorAuthorization",
        object_uuid=instance.pk,
        object_repr=(
            f"Sector: {instance.sector.name} | "
            f"Manager: {instance.permission.user.email}"
        ),
        deleted_by=user if user and not getattr(user, "is_anonymous", True) else None,
        project=instance.project,
    )
