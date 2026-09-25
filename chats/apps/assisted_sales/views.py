from urllib.parse import parse_qs, urlparse

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.apps.assisted_sales.exceptions import (
    CopilotConnectError,
    CopilotFeatureDisabled,
    CopilotIntegrationAlreadyExists,
)
from chats.apps.assisted_sales.feature_flags import is_assisted_sales_copilot_enabled
from chats.apps.assisted_sales.models import CopilotIntegration, CopilotMessageFeedback
from chats.apps.assisted_sales.serializers import (
    CopilotConnectionSerializer,
    CopilotExistingProjectSerializer,
    CopilotIntegrationResponseSerializer,
    CopilotLinkedProjectSerializer,
    CopilotMessageFeedbackSerializer,
    CreateCopilotIntegrationSerializer,
    UpdateCopilotIntegrationSerializer,
)
from chats.apps.assisted_sales.usecases import (
    CheckCopilotCreatePermissionUseCase,
    CreateCopilotIntegrationUseCase,
    GetCopilotMessageFeedbackUseCase,
    GetLinkedCopilotUseCase,
    ListCopilotConnectionsUseCase,
    ListCopilotRoomMessagesUseCase,
    ListExistingCopilotsUseCase,
    RemoveCopilotIntegrationUseCase,
    SubmitCopilotMessageFeedbackUseCase,
    UpdateOrLinkCopilotUseCase,
)
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

HTTP_CLIENT_ERROR_MIN = 400
HTTP_SERVER_ERROR_MAX = 600


def _copilot_feature_forbidden():
    return Response(
        {"status_code": status.HTTP_403_FORBIDDEN, "error": "Forbidden"},
        status=status.HTTP_403_FORBIDDEN,
    )


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

        if not is_assisted_sales_copilot_enabled(project.uuid):
            return _copilot_feature_forbidden()

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
                authorization=request.META.get("HTTP_AUTHORIZATION", ""),
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
                if HTTP_CLIENT_ERROR_MIN <= exc.status_code < HTTP_SERVER_ERROR_MAX
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
            integration = UpdateOrLinkCopilotUseCase().execute(
                uuid=uuid,
                new_uuid=serializer.validated_data["new_uuid"],
                user=request.user,
            )
        except Project.DoesNotExist:
            return Response(
                {"status_code": status.HTTP_404_NOT_FOUND, "error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDenied:
            return Response(
                {"status_code": status.HTTP_403_FORBIDDEN, "error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except CopilotFeatureDisabled:
            return _copilot_feature_forbidden()
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
                if HTTP_CLIENT_ERROR_MIN <= exc.status_code < HTTP_SERVER_ERROR_MAX
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

        if not is_assisted_sales_copilot_enabled(integration.project_id):
            return _copilot_feature_forbidden()

        try:
            RemoveCopilotIntegrationUseCase().execute(integration=integration)
        except CopilotConnectError as exc:
            return Response(
                {"status_code": exc.status_code, "error": exc.error},
                status=exc.status_code
                if HTTP_CLIENT_ERROR_MIN <= exc.status_code < HTTP_SERVER_ERROR_MAX
                else status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"status": 200}, status=status.HTTP_200_OK)


class CopilotLinkedProjectView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_uuid):
        try:
            project = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            return Response(
                {"status_code": status.HTTP_404_NOT_FOUND, "error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not ProjectPermission.objects.filter(
            user=request.user, project=project
        ).exists():
            return Response(
                {"status_code": status.HTTP_403_FORBIDDEN, "error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not is_assisted_sales_copilot_enabled(project.uuid):
            return _copilot_feature_forbidden()

        sector = None
        sector_uuid = request.query_params.get("sector")
        if sector_uuid:
            try:
                sector = Sector.objects.get(uuid=sector_uuid, project=project)
            except Sector.DoesNotExist:
                return Response(
                    {"status_code": status.HTTP_404_NOT_FOUND, "error": "Not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        try:
            integration = GetLinkedCopilotUseCase().execute(
                project=project, sector=sector
            )
        except CopilotIntegration.DoesNotExist:
            return Response({}, status=status.HTTP_200_OK)

        return Response(
            CopilotLinkedProjectSerializer(integration).data,
            status=status.HTTP_200_OK,
        )


def _query_flag_is_true(raw) -> bool:
    if raw is None:
        return False
    return str(raw).strip().lower() in ("true", "1", "yes")


class CopilotListConnectionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_uuid):
        try:
            project = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            return Response(
                {"status_code": status.HTTP_404_NOT_FOUND, "error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not ProjectPermission.objects.filter(
            user=request.user, project=project
        ).exists():
            return Response(
                {"status_code": status.HTTP_403_FORBIDDEN, "error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not is_assisted_sales_copilot_enabled(project.uuid):
            return _copilot_feature_forbidden()

        integrations = ListCopilotConnectionsUseCase().execute(
            project=project,
            is_principal=_query_flag_is_true(request.query_params.get("is_principal")),
        )
        return Response(
            CopilotConnectionSerializer(integrations, many=True).data,
            status=status.HTTP_200_OK,
        )


class CopilotCreatePermissionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_uuid):
        try:
            project = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            return Response(
                {"status_code": status.HTTP_404_NOT_FOUND, "error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not ProjectPermission.objects.filter(
            user=request.user, project=project
        ).exists():
            return Response(
                {"status_code": status.HTTP_403_FORBIDDEN, "error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not is_assisted_sales_copilot_enabled(project.uuid):
            return _copilot_feature_forbidden()

        try:
            can_create = CheckCopilotCreatePermissionUseCase().execute(
                project_uuid=str(project.uuid),
                user_email=request.user.email,
            )
        except CopilotConnectError as exc:
            return Response(
                {"status_code": exc.status_code, "error": exc.error},
                status=exc.status_code
                if HTTP_CLIENT_ERROR_MIN <= exc.status_code < HTTP_SERVER_ERROR_MAX
                else status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"can_create": can_create}, status=status.HTTP_200_OK)


class CopilotExistingProjectsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, org_uuid):
        project_ids = ProjectPermission.objects.filter(
            user=request.user, project__org=str(org_uuid)
        ).values_list("project_id", flat=True)
        if not project_ids:
            return Response(
                {"status_code": status.HTTP_403_FORBIDDEN, "error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not any(
            is_assisted_sales_copilot_enabled(project_id) for project_id in project_ids
        ):
            return _copilot_feature_forbidden()

        try:
            projects = ListExistingCopilotsUseCase().execute(
                org_uuid=str(org_uuid),
                name=request.query_params.get("name") or None,
                authorization=request.META.get("HTTP_AUTHORIZATION", ""),
            )
        except CopilotConnectError as exc:
            return Response(
                {"status_code": exc.status_code, "error": exc.error},
                status=exc.status_code
                if HTTP_CLIENT_ERROR_MIN <= exc.status_code < HTTP_SERVER_ERROR_MAX
                else status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            CopilotExistingProjectSerializer(projects, many=True).data,
            status=status.HTTP_200_OK,
        )


def _rewrite_pagination_url(request, flows_url):
    if not flows_url:
        return None
    cursor = parse_qs(urlparse(str(flows_url)).query).get("cursor", [None])[0]
    if not cursor:
        return None
    params = request.query_params.copy()
    params["cursor"] = cursor
    return request.build_absolute_uri(f"{request.path}?{params.urlencode()}")


class CopilotRoomMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_uuid):
        project_uuid = request.query_params.get("project")
        if not project_uuid:
            return Response(
                {
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "error": "Project not provided",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(uuid=project_uuid)
        except (Project.DoesNotExist, ValueError, ValidationError):
            return Response(
                {"status_code": status.HTTP_404_NOT_FOUND, "error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not ProjectPermission.objects.filter(
            user=request.user, project=project
        ).exists():
            return Response(
                {"status_code": status.HTTP_403_FORBIDDEN, "error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not is_assisted_sales_copilot_enabled(project.uuid):
            return _copilot_feature_forbidden()

        try:
            data = ListCopilotRoomMessagesUseCase().execute(
                project=project,
                room_uuid=room_uuid,
                cursor=request.query_params.get("cursor") or None,
            )
        except Room.DoesNotExist:
            return Response(
                {"status_code": status.HTTP_404_NOT_FOUND, "error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except CopilotIntegration.DoesNotExist:
            return Response(
                {"status_code": status.HTTP_404_NOT_FOUND, "error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except CopilotConnectError as exc:
            return Response(
                {"status_code": exc.status_code, "error": exc.error},
                status=exc.status_code
                if 400 <= exc.status_code < 600
                else status.HTTP_502_BAD_GATEWAY,
            )

        if isinstance(data, dict):
            data["next"] = _rewrite_pagination_url(request, data.get("next"))
            data["previous"] = _rewrite_pagination_url(request, data.get("previous"))

        return Response(data, status=status.HTTP_200_OK)


class CopilotMessageFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def _error_response(self, exc):
        if isinstance(exc, (Room.DoesNotExist, CopilotMessageFeedback.DoesNotExist)):
            return Response(
                {"status_code": status.HTTP_404_NOT_FOUND, "error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if isinstance(exc, PermissionDenied):
            return Response(
                {"status_code": status.HTTP_403_FORBIDDEN, "error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if isinstance(exc, CopilotFeatureDisabled):
            return _copilot_feature_forbidden()
        raise exc

    def get(self, request, room_uuid):
        message_id = request.query_params.get("message_id")
        try:
            result = GetCopilotMessageFeedbackUseCase().execute(
                user=request.user,
                room_uuid=room_uuid,
                message_id=message_id,
            )
        except (
            Room.DoesNotExist,
            CopilotMessageFeedback.DoesNotExist,
            PermissionDenied,
            CopilotFeatureDisabled,
        ) as exc:
            return self._error_response(exc)

        if message_id is not None:
            return Response(
                CopilotMessageFeedbackSerializer(result).data,
                status=status.HTTP_200_OK,
            )

        return Response(
            {"results": CopilotMessageFeedbackSerializer(result, many=True).data},
            status=status.HTTP_200_OK,
        )

    def post(self, request, room_uuid):
        serializer = CopilotMessageFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            feedback, created = SubmitCopilotMessageFeedbackUseCase().execute(
                user=request.user,
                room_uuid=room_uuid,
                message_id=data["message_id"],
                liked=data["liked"],
                text=data.get("text"),
                tags=data.get("tags"),
            )
        except (Room.DoesNotExist, PermissionDenied, CopilotFeatureDisabled) as exc:
            return self._error_response(exc)

        return Response(
            CopilotMessageFeedbackSerializer(feedback).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
