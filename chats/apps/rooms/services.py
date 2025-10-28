import csv
import io
import logging
import time

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _
from sentry_sdk import capture_message

from chats.apps.projects.models.models import Project
from chats.core.cache import CacheClient

from .models import Room

logger = logging.getLogger(__name__)


def can_retrieve(room, user, project) -> bool:
    filter_project_uuid = models.Q(queue__sector__project__uuid=project)
    is_sector_manager = models.Q(queue__sector__authorizations__permission__user=user)
    is_project_admin = models.Q(
        models.Q(queue__sector__project__permissions__user=user)
        & models.Q(queue__sector__project__permissions__role=1)
    )
    is_user_assigned_to_room = models.Q(user=user)
    check_admin_manager_agent_role_filter = models.Q(
        filter_project_uuid
        & (is_sector_manager | is_project_admin | is_user_assigned_to_room)
    )

    rooms_check = Room.objects.filter(
        check_admin_manager_agent_role_filter,
    ).exists()
    return rooms_check


class RoomsReportService:
    """
    Service for generating rooms reports.
    """

    def __init__(self, project: Project):
        self.project = project
        self.cache_client = CacheClient()
        self.cache_ttl = 300  # 5 minutes

    def get_cache_key(self) -> str:
        """
        Get the cache key for the rooms report.
        """

        return f"rooms_report_{self.project.uuid}"

    def is_generating_report(self) -> bool:
        """
        Check if a report is already being generated.
        """

        return self.cache_client.get(self.get_cache_key())

    def generate_report(self, filters: dict, recipient_email: str) -> str:
        """
        Generate a rooms report and send it to the email address provided.
        """

        logger.info("Generating report for project %s", self.project.uuid)

        self.cache_client.set(
            self.get_cache_key(),
            "true",
            ex=self.cache_ttl,
        )

        start_time = time.time()
        output = None

        try:
            rooms = (
                Room.objects.filter(queue__sector__project=self.project, **filters)
                .order_by("created_on")
                .select_related("user", "contact", "queue", "queue__sector", "metric")
            ).prefetch_related("tags")

            if not rooms.exists():
                logger.info("No rooms found for project %s", self.project.uuid)
                return

            logger.info(
                "Rooms found for project %s: %s", self.project.uuid, rooms.count()
            )

            # Create CSV file in memory
            output = io.StringIO()
            writer = csv.writer(output)

            # Hardcoded in portuguese for now
            writer.writerow(
                [
                    "Identificador da sala",
                    "Cliente",
                    "Número do cliente",
                    "Data da entrada",
                    "Data de fim",
                    "Fila",
                    "Agente",
                    "Quantidade de mensagens",
                    "Tempo de espera",
                    "Tempo para primeira resposta",
                    "Tempo de resposta",
                    "Duração",
                    "Tags",
                ]
            )

            # Write data rows
            for room in rooms:
                urn = room.urn
                phone_number = urn.split(":")[1]

                tags = ", ".join([tag.name for tag in room.tags.all()])

                writer.writerow(
                    [
                        room.uuid,
                        room.contact.name,
                        phone_number,
                        room.created_on,
                        room.ended_at,
                        room.queue.name,
                        room.user.name if room.user else None,
                        room.messages.count(),
                        room.metric.waiting_time,
                        room.metric.first_response_time,
                        room.metric.message_response_time,
                        room.metric.interaction_time,
                        tags,
                    ]
                )

            # Get CSV content
            csv_content = output.getvalue()

            end_time = time.time()
            time_taken = int(end_time - start_time)

            logger.info(
                "Report generated for project %s in %s seconds",
                self.project.uuid,
                time_taken,
            )

            if settings.SEND_EMAILS:
                logger.info(
                    "Sending rooms report for project %s via email to %s",
                    self.project.uuid,
                    recipient_email,
                )

                dt = timezone.now().strftime("%d/%m/%Y_%H-%M-%S")
                subject = _("Rooms report for project %(project)s - %(date)s") % {
                    'project': self.project.name,
                    'date': dt
                }
                
                context = {
                    'project_name': self.project.name,
                    'generation_date': timezone.now().strftime("%d/%m/%Y at %H:%M:%S"),
                    'total_rooms': rooms.count(),
                    'current_year': timezone.now().year,
                }

                html_content = render_to_string('rooms/emails/report_is_ready.html', context)
                text_content = _("The rooms report for project %(project)s is ready and attached to this email.") % {
                    'project': self.project.name
                }

                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient_email],
                )
                email.attach_alternative(html_content, "text/html")
                email.attach("rooms_report.csv", csv_content, "text/csv")
                email.send(fail_silently=False)

                logger.info(
                    "Rooms report for project %s sent to %s",
                    self.project.uuid,
                    recipient_email,
                )

        except Exception as e:
            logger.error(
                "Error generating report for project %s: %s", self.project.uuid, e
            )
            capture_message(e)

            if settings.SEND_EMAILS:
                logger.info(
                    "Sending error notification for rooms report of project %s to %s",
                    self.project.uuid,
                    recipient_email,
                )

                dt = timezone.now().strftime("%d/%m/%Y_%H-%M-%S")
                subject = _("Error generating rooms report for project %(project)s - %(date)s") % {
                    'project': self.project.name,
                    'date': dt
                }
                
                context = {
                    'project_name': self.project.name,
                    'error_message': str(e),
                    'current_year': timezone.now().year,
                }

                html_content = render_to_string('rooms/emails/report_failed.html', context)
                text_content = _(
                    "An error occurred while generating the rooms report for project %(project)s.\n\n"
                    "Error: %(error)s\n\n"
                    "Please try again later or contact support."
                ) % {
                    'project': self.project.name,
                    'error': str(e)
                }

                try:
                    email = EmailMultiAlternatives(
                        subject=subject,
                        body=text_content,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[recipient_email],
                    )
                    email.attach_alternative(html_content, "text/html")
                    email.send(fail_silently=False)

                    logger.info(
                        "Error notification sent to %s for project %s",
                        recipient_email,
                        self.project.uuid,
                    )
                except Exception as email_error:
                    logger.error(
                        "Failed to send error notification email: %s", email_error
                    )

        finally:
            if output is not None:
                output.close()

        self.cache_client.delete(self.get_cache_key())