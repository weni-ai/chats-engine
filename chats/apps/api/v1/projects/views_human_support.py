import logging

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.apps.api.v1.internal.rest_clients.nexus_rest_client import NexusRESTClient
from chats.apps.projects.models import ProjectPermission
from chats.core.cache_utils import (
    get_nexus_settings_cached,
    set_nexus_settings_cache,
)

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

        cached = get_nexus_settings_cached(project_uuid)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        client = NexusRESTClient()
        try:
            response = client.get_human_support(project_uuid)
        except Exception:
            logger.exception("Failed to reach NEXUS API for project %s", project_uuid)
            return Response(
                {"error": "Failed to reach NEXUS API"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            set_nexus_settings_cache(project_uuid, data)
            return Response(data, status=status.HTTP_200_OK)

        try:
            error_body = response.json()
        except Exception:
            error_body = {"error": response.text}

        return Response(error_body, status=response.status_code)

    def patch(self, request, project_uuid):
        self.check_project_permission(request, project_uuid)

        data = request.data

        if not data or not isinstance(data, dict):
            return Response(
                {"error": "Request body must be a JSON object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        has_human_support = "human_support" in data
        has_prompt = "human_support_prompt" in data

        if not has_human_support and not has_prompt:
            return Response(
                {
                    "error": "At least one of 'human_support' or 'human_support_prompt' is required"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if has_human_support and not isinstance(data["human_support"], bool):
            return Response(
                {"error": "human_support must be a boolean"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if has_prompt and not isinstance(data["human_support_prompt"], str):
            return Response(
                {"error": "human_support_prompt must be a string"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = {}
        if has_human_support:
            payload["human_support"] = data["human_support"]
        if has_prompt:
            payload["human_support_prompt"] = data["human_support_prompt"]

        client = NexusRESTClient()
        try:
            response = client.patch_human_support(project_uuid, payload)
        except Exception:
            logger.exception("Failed to reach NEXUS API for project %s", project_uuid)
            return Response(
                {"error": "Failed to reach NEXUS API"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            set_nexus_settings_cache(project_uuid, response_data)
            return Response(response_data, status=status.HTTP_200_OK)

        try:
            error_body = response.json()
        except Exception:
            error_body = {"error": response.text}

        return Response(error_body, status=response.status_code)
