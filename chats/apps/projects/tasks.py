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
    
    # DEBUG: Log every call to this task
    logger.info(
        f"🔍 log_agent_status_change CALLED: agent={agent_email}, "
        f"status={status}, custom_status={custom_status_name}, "
        f"custom_status_uuid={custom_status_type_uuid}"
    )
    
    try:
        agent = User.objects.get(email=agent_email)
        project = Project.objects.get(uuid=project_uuid)
        
        # If custom_status is not provided, check if there's an active one
        if custom_status_name is None and custom_status_type_uuid is None:
            from chats.apps.projects.models.models import CustomStatus
            
            active_custom_status = CustomStatus.objects.filter(
                user=agent,
                project=project,
                is_active=True
            ).first()
            
            if active_custom_status:
                custom_status_name = active_custom_status.status_type.name
                custom_status_type_uuid = active_custom_status.status_type.uuid
        
        # Get agent's local date based on project timezone
        project_tz = project.timezone
        now = timezone.now()
        local_now = now.astimezone(project_tz)
        log_date = local_now.date()
        
        # Prepare status change entry with cleaner format
        if status == "ONLINE":
            # ONLINE: only status and timestamp
            status_entry = {
                "status": "ONLINE",
                "timestamp": local_now.isoformat(),
            }
        elif status == "OFFLINE" and custom_status_name is None:
            # OFFLINE without custom status: only status and timestamp
            status_entry = {
                "status": "OFFLINE",
                "timestamp": local_now.isoformat(),
            }
        else:
            # OFFLINE with custom status: change to BREAK and include details
            status_entry = {
                "status": "BREAK",
                "timestamp": local_now.isoformat(),
                "custom_status": custom_status_name,
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
                # Check if the last status change is the same to avoid duplicates
                last_change = log.status_changes[-1] if log.status_changes else None
                
                if last_change:
                    # Compare entries considering the new format
                    last_status = last_change.get("status")
                    last_custom = last_change.get("custom_status")
                    last_type_uuid = last_change.get("status_type_uuid")
                    
                    new_status = status_entry.get("status")
                    new_custom = status_entry.get("custom_status")
                    new_type_uuid = status_entry.get("status_type_uuid")
                    
                    is_duplicate = (
                        last_status == new_status and
                        last_custom == new_custom and
                        last_type_uuid == new_type_uuid
                    )
                    
                    if is_duplicate:
                        logger.info(
                            f"Skipping duplicate status change for agent {agent_email} in project {project.name}: "
                            f"{new_status} {f'({new_custom})' if new_custom else ''}"
                        )
                        return
                
                # Append to existing log
                log.status_changes.append(status_entry)
                log.save(update_fields=["status_changes", "modified_on"])
                
            logger.info(
                f"Status change logged for agent {agent_email} in project {project.name}: "
                f"{status_entry.get('status')} {f\"({status_entry.get('custom_status')})\" if status_entry.get('custom_status') else ''}"
            )
            
    except Exception as e:
        logger.error(f"Error logging agent status change: {e}", exc_info=True)
        raise
