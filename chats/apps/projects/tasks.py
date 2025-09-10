from chats.celery import app
from django.contrib.auth import get_user_model

from chats.apps.projects.models import Project
from chats.apps.projects.models.models import AgentDisconnectLog


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
