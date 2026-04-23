import logging

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.apps.api.v1.human_support.serializers import (
    HumanSupportNexusSettingsSerializer,
)
from chats.apps.api.v1.human_support.service import HumanSupportNexusService
from chats.apps.projects.models import ProjectPermission

logger = logging.getLogger(__name__)


class HumanSupportNexusSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def check_project_permission(self, request, project_uuid):
        if not ProjectPermission.objects.filter(
            user=request.user, project__uuid=project_uuid
        ).exists():
            raise PermissionDenied()

    def get(self, request, project_uuid):
        self.check_project_permission(request, project_uuid)

        service = HumanSupportNexusService()
        try:
            data, status_code = service.get_settings(project_uuid)
        except Exception:
            logger.exception("Failed to reach NEXUS API for project %s", project_uuid)
            return Response(
                {"error": "Failed to reach NEXUS API"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(data, status=status_code)

    def patch(self, request, project_uuid):
        self.check_project_permission(request, project_uuid)

        serializer = HumanSupportNexusSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = HumanSupportNexusService()
        try:
            data, status_code = service.update_settings(
                project_uuid, serializer.validated_data
            )
        except Exception:
            logger.exception("Failed to reach NEXUS API for project %s", project_uuid)
            return Response(
                {"error": "Failed to reach NEXUS API"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(data, status=status_code)
