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


_METRIC_LABELS = {
    "waiting_time": _("Waiting time"),
    "first_response_time": _("First response time"),
    "conversation_duration": _("Conversation duration"),
}


def _format_seconds_to_friendly(total_seconds: int) -> str:
    if total_seconds is None:
        return "—"
    seconds = max(0, int(total_seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def get_metric_goal_alert_email(
    project_name: str,
    metric: str,
    violating_count: int,
    threshold_seconds: int,
    max_value_seconds: int,
    rooms_threshold_count: int,
):
    """Returns ``(plain_text, html)`` for the metric goal alert email."""
    metric_label = _METRIC_LABELS.get(metric, metric)
    threshold_friendly = _format_seconds_to_friendly(threshold_seconds)
    max_friendly = _format_seconds_to_friendly(max_value_seconds)

    context = {
        "project_name": project_name,
        "metric": metric,
        "metric_label": metric_label,
        "violating_count": violating_count,
        "threshold_seconds": threshold_seconds,
        "threshold_friendly": threshold_friendly,
        "max_value_seconds": max_value_seconds,
        "max_value_friendly": max_friendly,
        "rooms_threshold_count": rooms_threshold_count,
        "current_year": timezone.now().year,
    }

    try:
        html = render_to_string("rooms/emails/metric_goal_alert.html", context)
    except Exception:
        html = None

    plain_text = _(
        "Metric goal violation detected for project %(project)s.\n\n"
        "Metric: %(metric)s\n"
        "Rooms in violation: %(count)s (threshold: %(threshold_count)s)\n"
        "Configured limit: %(threshold)s\n"
        "Worst current value: %(max_value)s"
    ) % {
        "project": project_name,
        "metric": metric_label,
        "count": violating_count,
        "threshold_count": rooms_threshold_count,
        "threshold": threshold_friendly,
        "max_value": max_friendly,
    }

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
        "An error occurred while generating the custom report for project %(project)s.\n\n"
        "Error: %(error)s\n\nPlease try again later or contact support."
    ) % {"project": project_name, "error": error_message or _("Unknown error")}

    return plain_text, html
