import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from chats.apps.projects.models import Project
from chats.apps.projects.models.models import AgentDisconnectLog, AgentStatusLog
from chats.celery import app

logger = logging.getLogger(__name__)


@app.task
def create_agent_disconnect_log(
    project_uuid: str, agent_email: str, disconnected_by_email: str
):
    User = get_user_model()
    project = Project.objects.get(uuid=project_uuid)
    agent = User.objects.get(email=agent_email)
    disconnected_by = User.objects.get(email=disconnected_by_email)
    AgentDisconnectLog.objects.create(
        project=project,
        agent=agent,
        disconnected_by=disconnected_by,
    )


@app.task(name="projects.log_agent_status_change")
def log_agent_status_change(
    agent_email: str,
    project_uuid: str,
    status: str,
    custom_status_name: str = None,
    custom_status_type_uuid: str = None,
):
    """
    Create or update daily agent status log.

    Args:
        agent_email: Agent email
        project_uuid: Project UUID
        status: ONLINE or OFFLINE
        custom_status_name: Name of custom status (if applicable)
        custom_status_type_uuid: UUID of custom status type (if applicable)
    """
    User = get_user_model()

    try:
        agent = User.objects.get(email=agent_email)
        project = Project.objects.get(uuid=project_uuid)

        if custom_status_name is None and custom_status_type_uuid is None:
            from chats.apps.projects.models.models import CustomStatus

            active_custom_status = CustomStatus.objects.filter(
                user=agent, project=project, is_active=True
            ).first()

            if active_custom_status:
                custom_status_name = active_custom_status.status_type.name
                custom_status_type_uuid = active_custom_status.status_type.uuid

        project_tz = project.timezone
        now = timezone.now()
        local_now = now.astimezone(project_tz)
        log_date = local_now.date()

        if status == "ONLINE":
            status_entry = {
                "status": "ONLINE",
                "timestamp": local_now.isoformat(),
            }
        elif status == "OFFLINE" and custom_status_name is None:
            status_entry = {
                "status": "OFFLINE",
                "timestamp": local_now.isoformat(),
            }
        else:
            status_entry = {
                "status": "BREAK",
                "timestamp": local_now.isoformat(),
                "custom_status": custom_status_name,
            }

        with transaction.atomic():
            log, created = AgentStatusLog.objects.select_for_update().get_or_create(
                agent=agent,
                project=project,
                log_date=log_date,
                defaults={"status_changes": [status_entry]},
            )

            if not created:
                last_change = log.status_changes[-1] if log.status_changes else None

                if last_change:
                    last_status = last_change.get("status")
                    last_custom = last_change.get("custom_status")
                    last_type_uuid = last_change.get("status_type_uuid")

                    new_status = status_entry.get("status")
                    new_custom = status_entry.get("custom_status")
                    new_type_uuid = status_entry.get("status_type_uuid")

                    is_duplicate = (
                        last_status == new_status
                        and last_custom == new_custom
                        and last_type_uuid == new_type_uuid
                    )

                    if is_duplicate:
                        return

                log.status_changes.append(status_entry)
                log.save(update_fields=["status_changes", "modified_on"])

    except Exception as e:
        logger.error(f"Error logging agent status change: {e}", exc_info=True)
        raise
