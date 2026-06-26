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
        "The chat export for the %(project)s project is ready.\n\n"
        "Copy and paste the URL below to download it:\n\n%(url)s"
    ) % {"project": project_name, "url": download_url}

    return plain_text, html


def get_report_failed_email(project_name: str, error_message: str = None):
    """
    Returns (plain_text, html) for report failed email.

    Args:
        project_name: Name of the project
        error_message: Error message to display

    Returns:
        Tuple of (plain_text_body, html_body)
    """
    context = {
        "project_name": project_name,
        "error_message": error_message,
        "current_year": timezone.now().year,
    }

    html = render_to_string("rooms/emails/report_failed.html", context)

    plain_text = _(
        "Unable to generate chat export for the %(project)s project.\n\n"
        "Error: %(error)s\n\nTry again later or contact support."
    ) % {"project": project_name, "error": error_message or _("Unknown error")}

    return plain_text, html
