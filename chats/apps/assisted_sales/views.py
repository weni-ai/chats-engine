from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.apps.assisted_sales.exceptions import (
    CopilotConnectError,
    CopilotIntegrationAlreadyExists,
)
from chats.apps.assisted_sales.models import CopilotIntegration
from chats.apps.assisted_sales.serializers import (
    CopilotIntegrationResponseSerializer,
    CreateCopilotIntegrationSerializer,
    UpdateCopilotIntegrationSerializer,
)
from chats.apps.assisted_sales.usecases import (
    CreateCopilotIntegrationUseCase,
    RemoveCopilotIntegrationUseCase,
    UpdateCopilotIntegrationUseCase,
)
from chats.apps.projects.models import ProjectPermission


class CopilotProjectCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = dict(request.data)
        if "project" not in payload and request.query_params.get("project"):
            payload["project"] = request.query_params.get("project")
        if "sector" not in payload and request.query_params.get("sector"):
            payload["sector"] = request.query_params.get("sector")

        serializer = CreateCopilotIntegrationSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        project = serializer.validated_data["project"]
        if not ProjectPermission.objects.filter(
            user=request.user, project=project
        ).exists():
            return Response(
                {"status_code": status.HTTP_403_FORBIDDEN, "error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        sector = serializer.validated_data.get("sector")
        if sector and sector.project_id != project.uuid:
            return Response(
                {
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "error": "Sector does not belong to this project",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            integration = CreateCopilotIntegrationUseCase().execute(
                name=serializer.validated_data["name"],
                project=project,
                user=request.user,
                sector=sector,
            )
        except CopilotIntegrationAlreadyExists:
            return Response(
                {
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "error": "Copilot integration already exists for this project",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except CopilotConnectError as exc:
            return Response(
                {"status_code": exc.status_code, "error": exc.error},
                status=exc.status_code
                if 400 <= exc.status_code < 600
                else status.HTTP_502_BAD_GATEWAY,
            )
        except (TypeError, ValueError, KeyError) as exc:
            return Response(
                {"status_code": status.HTTP_502_BAD_GATEWAY, "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            CopilotIntegrationResponseSerializer(integration).data,
            status=status.HTTP_200_OK,
        )


class CopilotProjectUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, uuid):
        serializer = UpdateCopilotIntegrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            integration = CopilotIntegration.objects.select_related("project").get(
                Q(uuid=uuid) | Q(copilot_project_uuid=uuid)
            )
        except CopilotIntegration.DoesNotExist:
            return Response(
                {"status_code": status.HTTP_404_NOT_FOUND, "error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not ProjectPermission.objects.filter(
            user=request.user, project=integration.project
        ).exists():
            return Response(
                {"status_code": status.HTTP_403_FORBIDDEN, "error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            integration = UpdateCopilotIntegrationUseCase().execute(
                integration=integration,
                new_uuid=serializer.validated_data["new_uuid"],
                user=request.user,
            )
        except CopilotConnectError as exc:
            return Response(
                {"status_code": exc.status_code, "error": exc.error},
                status=exc.status_code
                if 400 <= exc.status_code < 600
                else status.HTTP_502_BAD_GATEWAY,
            )
        except (TypeError, ValueError, KeyError) as exc:
            return Response(
                {"status_code": status.HTTP_502_BAD_GATEWAY, "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            CopilotIntegrationResponseSerializer(integration).data,
            status=status.HTTP_200_OK,
        )


class CopilotProjectRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, uuid):
        try:
            integration = CopilotIntegration.objects.select_related("project").get(
                Q(uuid=uuid) | Q(copilot_project_uuid=uuid)
            )
        except CopilotIntegration.DoesNotExist:
            return Response(
                {"status_code": status.HTTP_404_NOT_FOUND, "error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not ProjectPermission.objects.filter(
            user=request.user, project=integration.project
        ).exists():
            return Response(
                {"status_code": status.HTTP_403_FORBIDDEN, "error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            RemoveCopilotIntegrationUseCase().execute(integration=integration)
        except CopilotConnectError as exc:
            return Response(
                {"status_code": exc.status_code, "error": exc.error},
                status=exc.status_code
                if 400 <= exc.status_code < 600
                else status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"status": 200}, status=status.HTTP_200_OK)
