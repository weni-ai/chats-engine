from django.db.models.signals import pre_delete
from django.dispatch import receiver

from chats.apps.sectors.models import SectorAuthorization


@receiver(pre_delete, sender=SectorAuthorization)
def log_sector_authorization_deletion(sender, instance, **kwargs):
    from chats.apps.projects.models import DeletionLog

    DeletionLog.objects.create(
        model_name="SectorAuthorization",
        object_uuid=instance.pk,
        object_repr=(
            f"Sector: {instance.sector.name} | "
            f"Manager: {instance.permission.user.email}"
        ),
        deleted_by=getattr(instance, "deleted_by", None),
        project=instance.project,
    )
