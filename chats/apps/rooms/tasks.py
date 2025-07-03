from uuid import UUID
from chats.apps.projects.models.models import Project
from chats.apps.rooms.services import RoomsReportService
from chats.celery import app


@app.task
def generate_rooms_report(project_uuid: UUID, filters: dict, recipient_email: str):
    """
    Generate a report of the rooms in the project.
    """
    project = Project.objects.get(uuid=project_uuid)

    report_service = RoomsReportService(project)
    report_service.generate_report(filters, recipient_email)
