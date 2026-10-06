import logging

from django.conf import settings
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

logger = logging.getLogger(__name__)


def is_out_off_whatsapp_response_window_enabled(project_uuid) -> bool:
    if not project_uuid:
        return False
    try:
        return is_feature_active_for_attributes(
            settings.OUT_OFF_WHATSAPP_RESPONSE_WINDOW_FEATURE_FLAG_KEY,
            {"projectUUID": str(project_uuid)},
        )
    except Exception:
        logger.exception(
            "Failed to evaluate out off whatsapp response window feature flag for project %s",
            project_uuid,
        )
        return False
