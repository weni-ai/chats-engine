import logging

from chats.celery import app
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from chats.apps.projects.models import Project
from chats.apps.projects.models.models import AgentDisconnectLog, AgentStatusLog

logger = logging.getLogger(__name__)


@app.task
def create_agent_disconnect_log(project_uuid: str, agent_email: str, disconnected_by_email: str):
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
        
        # Get agent's local date based on project timezone
        project_tz = project.timezone
        now = timezone.now()
        local_now = now.astimezone(project_tz)
        log_date = local_now.date()
        
        # Prepare status change entry
        status_entry = {
            "timestamp": now.isoformat(),
            "status": status,
            "custom_status": custom_status_name,
            "status_type_uuid": str(custom_status_type_uuid) if custom_status_type_uuid else None,
        }
        
        with transaction.atomic():
            # Get or create log for today
            log, created = AgentStatusLog.objects.select_for_update().get_or_create(
                agent=agent,
                project=project,
                log_date=log_date,
                defaults={"status_changes": [status_entry]}
            )
            
            if not created:
                # Append to existing log
                log.status_changes.append(status_entry)
                log.save(update_fields=["status_changes", "modified_on"])
                
            logger.info(
                f"Status change logged for agent {agent_email} in project {project.name}: "
                f"{status} {f'({custom_status_name})' if custom_status_name else ''}"
            )
            
    except Exception as e:
        logger.error(f"Error logging agent status change: {e}", exc_info=True)
        raise
