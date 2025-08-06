import logging
import requests

from celery import shared_task
from django.conf import settings
from sentry_sdk import capture_exception

logger = logging.getLogger(__name__)


INSIGHTS_API_URL = settings.INSIGHTS_API_URL
INSIGHTS_API_MAX_RETRIES = settings.INSIGHTS_API_MAX_RETRIES
INSIGHTS_API_RETRY_DELAY = settings.INSIGHTS_API_RETRY_DELAY


@shared_task(
    bind=True,
    max_retries=INSIGHTS_API_MAX_RETRIES,
    default_retry_delay=INSIGHTS_API_RETRY_DELAY,
)
def send_secondary_project_to_insights(
    self, main_project_uuid: str, secondary_project_uuid: str
):
    """
    Send secondary project to Insights API to set it as secondary
    """
    try:
        url = f"{INSIGHTS_API_URL}/project/{secondary_project_uuid}/set-as-secondary/"
        body = {
            "main_project": str(main_project_uuid),
        }
        response = requests.post(url, json=body, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.error(
            "Error sending secondary project to Insights API: %s", exc, exc_info=True
        )
        capture_exception(exc)
        raise self.retry(exc=exc)
