import logging
from collections import defaultdict
from typing import List
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext as _

from chats.apps.projects.models.models import Project

logger = logging.getLogger(__name__)


class NotifyAdminsAboutNotFoundCSATFlow:
    def __init__(self, project: Project):
        self.project = project

    def execute(self):
        if not settings.SEND_EMAILS:
            return

        admins = self.project.admins.only("email", "language")

        if not admins.exists():
            logger.warning(
                "[CSAT FLOW SERVICE] No admin emails found for project %s (%s)",
                self.project.name,
                self.project.uuid,
            )
            return

        emails_by_language = defaultdict(list)
        for email, language in admins.values_list("email", "language"):
            lang = language if language else settings.DEFAULT_LANGUAGE
            emails_by_language[lang].append(email)

        for language, recipient_emails in emails_by_language.items():
            self._send_email(language, recipient_emails)

    def _send_email(self, language: str, recipient_emails: List[str]):
        with translation.override(language):
            context = {
                "project_name": self.project.name,
            }

            subject = _("Failed to start custom CSAT flow for project %(project)s") % {
                "project": self.project.name,
            }

            html_content = render_to_string(
                "csat/emails/custom_flow_not_found.html", context
            )
            text_content = _(
                "Failed to start custom CSAT flow for project %(project)s. "
                "Check if the flow still exists or update the "
                "sector configuration."
            ) % {"project": self.project.name}

        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_emails,
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)

            logger.info(
                "[CSAT FLOW SERVICE] Custom flow not found email sent to %s for project %s (%s)",
                recipient_emails,
                self.project.name,
                self.project.uuid,
            )
        except Exception as e:
            logger.error(
                "[CSAT FLOW SERVICE] Failed to send custom flow not found email for project %s (%s): %s",
                self.project.name,
                self.project.uuid,
                e,
            )
