import logging
import time
import csv
import io
from datetime import datetime
from django.db import models
from django.conf import settings

from chats.apps.projects.models.models import Project

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
    def __init__(self, project: Project):
        self.project = project

    def generate_report(self, filters: dict, recipient_email: str) -> str:
        logger.info("Generating report for project %s", self.project.uuid)

        rooms = (
            Room.objects.filter(queue__sector__project=self.project, **filters)
            .order_by("created_on")
            .select_related("user", "contact", "queue", "queue__sector")
        )

        if not rooms.exists():
            logger.info("No rooms found for project %s", self.project.uuid)
            return

        logger.info("Rooms found for project %s: %s", self.project.uuid, rooms.count())

        start_time = time.time()

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
            ]
        )

        # Write data rows
        for room in rooms:
            urn = room.urn
            phone_number = urn.split(":")[1]

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
                ]
            )

        # Get CSV content
        csv_content = output.getvalue()
        output.close()

        end_time = time.time()
        time_taken = int(end_time - start_time)

        logger.info(
            "Report generated for project %s in %s seconds",
            self.project.uuid,
            time_taken,
        )

        if settings.EMAIL_HOST:
            logger.info(
                "Sending rooms report for project %s via email to %s",
                self.project.uuid,
                recipient_email,
            )

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            subject = f"Relatório de salas do projeto {self.project.uuid} - {timestamp}"
            message = f"O relatório de salas do projeto {self.project.uuid} está pronto e foi anexado a este email."
            # Send email with CSV attachment
            from django.core.mail import EmailMessage

            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            email.attach("rooms_report.csv", csv_content, "text/csv")
            email.send(fail_silently=False)

            logger.info(
                "Rooms report for project %s sent to %s",
                self.project.uuid,
                recipient_email,
            )
