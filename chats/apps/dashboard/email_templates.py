from typing import Optional
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _


def get_report_ready_email(project_name: str, download_url: str):
    """
    Returns (plain_text, html) for report ready email.

    Args:
        project_name: Name of the project
        download_url: URL to download the report

    Returns:
        Tuple of (plain_text_body, html_body)
    """
    context = {
        "project_name": project_name,
        "download_url": download_url,
        "generation_date": timezone.now().strftime("%d/%m/%Y at %H:%M:%S"),
        "current_year": timezone.now().year,
    }

    html = render_to_string("rooms/emails/report_is_ready.html", context)

    plain_text = _(
        "The custom report for the project %(project)s is ready.\n\n"
        "Copy and paste the URL below to download the report:\n\n%(url)s"
    ) % {"project": project_name, "url": download_url}

    return plain_text, html


def get_report_failed_email(project_name: str, event_id: Optional[str] = None):
    """
    Returns (plain_text, html) for report failed email.

    Args:
        project_name: Name of the project
        event_id: Event ID to display

    Returns:
        Tuple of (plain_text_body, html_body)
    """
    context = {
        "project_name": project_name,
        "current_year": timezone.now().year,
        "event_id": event_id,
    }

    html = render_to_string("rooms/emails/report_failed.html", context)

    plain_text = _(
        "An error occurred while generating the custom report for project %(project)s.\n\n"
        "Event ID: %(event_id)s\n\nPlease try again later or contact support."
    ) % {"project": project_name, "event_id": event_id}

    return plain_text, html
