from django.conf import settings
from django.core.cache import cache

from chats.apps.dashboard.models import ReportStatus

REPORT_STATUS_CACHE_KEY_TEMPLATE = "report_status:{project_uuid}"
REPORT_STATUS_CACHE_TTL = settings.REPORT_STATUS_CACHE_TTL


class GetReportStatusUseCase:
    def execute(self, project):
        cache_key = REPORT_STATUS_CACHE_KEY_TEMPLATE.format(
            project_uuid=project.uuid,
        )

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        current_report = (
            ReportStatus.objects.filter(
                project=project, status__in=["pending", "in_progress"]
            )
            .order_by("created_on")
            .last()
        )

        if not current_report:
            data = {
                "status": "ready",
                "email": None,
                "report_uuid": None,
            }
        else:
            data = {
                "status": current_report.status,
                "email": current_report.user.email,
                "report_uuid": str(current_report.uuid),
            }

        cache.set(cache_key, data, REPORT_STATUS_CACHE_TTL)
        return data


class InvalidateReportStatusCacheUseCase:
    def execute(self, project_uuid):
        cache_key = REPORT_STATUS_CACHE_KEY_TEMPLATE.format(
            project_uuid=project_uuid,
        )
        cache.delete(cache_key)
