from django.db.models.signals import post_save
from django.dispatch import receiver

from chats.apps.dashboard.models import ReportStatus
from chats.apps.dashboard.usecases import InvalidateReportStatusCacheUseCase


@receiver(post_save, sender=ReportStatus)
def invalidate_report_status_cache_on_save(sender, instance, **kwargs):
    InvalidateReportStatusCacheUseCase().execute(
        project_uuid=str(instance.project_id),
    )
