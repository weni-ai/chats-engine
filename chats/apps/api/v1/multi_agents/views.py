import logging

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.apps.api.v1.multi_agents.service import MultiAgentsNexusService
from chats.apps.projects.models import ProjectPermission

logger = logging.getLogger(__name__)


class MultiAgentsView(APIView):
    permission_classes = [IsAuthenticated]

    def check_project_permission(self, request, project_uuid):
        if not ProjectPermission.objects.filter(
            user=request.user, project__uuid=project_uuid
        ).exists():
            raise PermissionDenied()

    def get(self, request, project_uuid):
        self.check_project_permission(request, project_uuid)

        service = MultiAgentsNexusService()
        try:
            data, status_code = service.get_multi_agents(project_uuid)
        except Exception:
            logger.exception("Failed to reach NEXUS API for project %s", project_uuid)
            return Response(
                {"error": "Failed to reach NEXUS API"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(data, status=status_code)
