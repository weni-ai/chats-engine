"""Email helpers for room exports.

Room exports reuse the existing report email templates (one email per file).
This module simply re-exports the helpers from the dashboard app so the
calling code does not depend on the dashboard module directly.
"""

from chats.apps.dashboard.email_templates import (
    get_report_failed_email as get_room_export_failed_email,
)
from chats.apps.dashboard.email_templates import (
    get_report_ready_email as get_room_export_ready_email,
)

__all__ = [
    "get_room_export_ready_email",
    "get_room_export_failed_email",
]
