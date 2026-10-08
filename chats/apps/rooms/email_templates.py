"""Email helpers for room exports.

These helpers render the room-export-specific templates (which use the
"chat export" wording) and return the (plain_text, html) tuple consumed by
`SendRoomExportEmail`.
"""

from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _


def get_room_export_ready_email(project_name: str, download_url: str):
    """Returns (plain_text, html) for the room export ready email."""
    context = {
        "project_name": project_name,
        "download_url": download_url,
        "generation_date": timezone.now().strftime("%d/%m/%Y at %H:%M:%S"),
        "current_year": timezone.now().year,
    }

    html = render_to_string("rooms/emails/room_export_is_ready.html", context)

    plain_text = _(
        "The chat export for the %(project)s project is ready.\n\n"
        "Copy and paste the URL below to download it:\n\n%(url)s"
    ) % {"project": project_name, "url": download_url}

    return plain_text, html


def get_room_export_failed_email(project_name: str, error_message: str = None):
    """Returns (plain_text, html) for the room export failed email."""
    context = {
        "project_name": project_name,
        "error_message": error_message,
        "current_year": timezone.now().year,
    }

    html = render_to_string("rooms/emails/room_export_failed.html", context)

    plain_text = _(
        "Unable to generate chat export for the %(project)s project.\n\n"
        "Error: %(error)s\n\nTry again later or contact support."
    ) % {"project": project_name, "error": error_message or _("Unknown error")}

    return plain_text, html


__all__ = [
    "get_room_export_ready_email",
    "get_room_export_failed_email",
]
