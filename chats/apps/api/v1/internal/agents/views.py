from chats.apps.api.v1.permissions import IsProjectAdminSpecific
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from django.contrib.auth import get_user_model

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.tasks import create_agent_disconnect_log
from chats.utils.websockets import send_channels_group
from django.conf import settings


class AgentDisconnectView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsProjectAdminSpecific]

    def post(self, request):
        project_uuid = request.data.get("project_uuid")
        agent_email = request.data.get("agent")

        if not project_uuid or not agent_email:
            raise NotFound(detail="Required fields not found")

        try:
            project = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            raise NotFound(detail="Project not found")

        User = get_user_model()
        try:
            target_user = User.objects.get(email=agent_email)
        except User.DoesNotExist:
            raise NotFound(detail="Agent not found")

        # Requester must be admin on the same project; attendants cannot disconnect others.
        try:
            requester_perm = ProjectPermission.objects.get(user=request.user, project=project)
        except ProjectPermission.DoesNotExist:
            raise PermissionDenied(detail="Not allowed on this project")
        if not requester_perm.is_admin:
            raise PermissionDenied(detail="Not allowed")

        # Target permission must exist
        try:
            target_perm = ProjectPermission.objects.get(user=target_user, project=project)
        except ProjectPermission.DoesNotExist:
            raise NotFound(detail="Agent permission not found")

        # Set target OFFLINE (no room transfers/closures here)
        if target_perm.status != ProjectPermission.STATUS_OFFLINE:
            target_perm.status = ProjectPermission.STATUS_OFFLINE
            target_perm.save(update_fields=["status"])

        # Send socket message to the agent
        send_channels_group(
            group_name=f"permission_{target_perm.pk}",
            call_type="notify",
            content={
                "user": target_user.email,
                "status": ProjectPermission.STATUS_OFFLINE,
                "user_disconnected_agent": request.user.email,
            },
            action="status.close",
        )

        # Create audit log via Celery (or inline if Celery disabled)
        if getattr(settings, "USE_CELERY", False):
            create_agent_disconnect_log.delay(str(project.uuid), target_user.email, request.user.email)
        else:
            create_agent_disconnect_log(str(project.uuid), target_user.email, request.user.email)  # type: ignore

        return Response(status=status.HTTP_200_OK)

