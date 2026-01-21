from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.internal.projects import serializers
from chats.apps.projects.models import CustomStatus, Project, ProjectPermission
from chats.apps.projects.usecases.status_service import InServiceStatusService
from chats.apps.queues.utils import (
    start_queue_priority_routing_for_all_queues_in_project,
)
from chats.core.cache_utils import get_user_id_by_email_cached

from chats.apps.rooms.models import Room
from chats.core.views import persist_keycloak_user_by_email

User = get_user_model()


class ProjectViewset(viewsets.ModelViewSet):
    swagger_tag = "Projects"
    queryset = Project.objects.all()
    serializer_class = serializers.ProjectInternalSerializer
    permission_classes = [IsAuthenticated, ModuleHasPermission]
    lookup_field = "uuid"

    def list(self, request, *args, **kwargs):
        """List projects for internal modules."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve the metadata of a project for internal modules."""
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a project through the internal service (syncing Keycloak when needed)."""
        if settings.OIDC_ENABLED:
            user_email = request.data.get("user_email")
            if user_email is None:
                raise ValidationError("user_email is a required field!")
            persist_keycloak_user_by_email(user_email)

        return super().create(request, *args, **kwargs)


class ProjectPermissionViewset(viewsets.ModelViewSet):
    swagger_tag = "Projects"
    queryset = ProjectPermission.objects.all()
    serializer_class = serializers.ProjectPermissionSerializer
    permission_classes = [IsAuthenticated, ModuleHasPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "project",
    ]
    lookup_field = "uuid"

    def get_object(self):
        if self.action in ["update", "partial_update"]:
            return None
        return super().get_object()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return serializers.ProjectPermissionReadSerializer
        return super().get_serializer_class()

    def list(self, request, *args, **kwargs):
        """List project permissions for administrative modules."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific project permission record."""
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a project permission (persisting the user in Keycloak when required)."""
        if settings.OIDC_ENABLED:
            user_email = request.data.get("user")
            persist_keycloak_user_by_email(user_email)
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {"detail": "This user already have permission on the project"},
                status.HTTP_400_BAD_REQUEST,
            )

    def update(
        self, request, *args, **kwargs
    ):  # TODO: GAMBIARRA ALERT! MOVE THIS LOGIC TO THE SERIALIZER or somewhere else
        """Update a project permission role/association for a user."""
        qs = self.queryset
        try:
            user_email = request.data["user"]
            role = request.data["role"]
            project_uuid = request.data["project"]
            persist_keycloak_user_by_email(user_email)
            email_l = (user_email or "").lower()
            uid = get_user_id_by_email_cached(email_l)
            if uid is None:
                return Response(
                    {"Detail": f"User {user_email} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            project = Project.objects.get(pk=project_uuid)

            permission = qs.get_or_create(user_id=email_l, project=project)[0]
            permission.role = role
            permission.save()
        except (KeyError, ProjectPermission.DoesNotExist):
            return Response(
                {
                    "Detail": "The correct required fields are: user(str), role(int) and project(str)"
                },
                status.HTTP_400_BAD_REQUEST,
            )
        except Project.DoesNotExist:
            return Response(
                {"Detail": f"The project {request.data['project']} does not exist yet"},
                status.HTTP_404_NOT_FOUND,
            )
        return Response({"Detail": "Updated"}, status.HTTP_200_OK)

    @action(detail=False, methods=["POST", "GET"], permission_classes=[IsAuthenticated])
    def status(self, request, *args, **kwargs):
        """Read or update the connection status for the current user's permission."""
        instance: ProjectPermission = None

        if request.method == "POST":
            project_uuid = request.data.get("project")
            instance = get_object_or_404(
                ProjectPermission, project__uuid=project_uuid, user=request.user
            )
            user_status = request.data.get("status")
            if user_status is None:
                return Response(
                    dict(connection_status=instance.status), status=status.HTTP_200_OK
                )

            if user_status.lower() == "online":
                instance.status = ProjectPermission.STATUS_ONLINE
                instance.save()

                # Log status change
                from chats.apps.projects.tasks import log_agent_status_change
                log_agent_status_change.delay(
                    agent_email=instance.user.email,
                    project_uuid=str(instance.project.uuid),
                    status="ONLINE",
                )

                room_count = Room.objects.filter(
                    user=instance.user,
                    queue__sector__project=instance.project,
                    is_active=True,
                ).count()

                has_other_priority = InServiceStatusService.has_priority_status(
                    instance.user, instance.project
                )

                if room_count > 0 and not has_other_priority:
                    in_service_type = InServiceStatusService.get_or_create_status_type(
                        instance.project
                    )

                    existing_in_service = CustomStatus.objects.filter(
                        user=instance.user,
                        status_type=in_service_type,
                        is_active=True,
                        project=instance.project,
                    ).exists()

                    if not existing_in_service:
                        CustomStatus.objects.create(
                            user=instance.user,
                            status_type=in_service_type,
                            is_active=True,
                            project=instance.project,
                            break_time=0,
                        )

            elif user_status.lower() == "offline":
                instance.status = ProjectPermission.STATUS_OFFLINE
                instance.save()

                # Log status change
                from chats.apps.projects.tasks import log_agent_status_change
                log_agent_status_change.delay(
                    agent_email=instance.user.email,
                    project_uuid=str(instance.project.uuid),
                    status="OFFLINE",
                )

                in_service_type = InServiceStatusService.get_or_create_status_type(
                    instance.project
                )
                in_service_status = CustomStatus.objects.filter(
                    user=instance.user,
                    status_type=in_service_type,
                    is_active=True,
                    project=instance.project,
                ).first()

                if in_service_status:
                    project_tz = instance.project.timezone
                    end_time = timezone.now().astimezone(project_tz)
                    created_on = in_service_status.created_on.astimezone(project_tz)
                    service_duration = end_time - created_on
                    in_service_status.is_active = False
                    in_service_status.break_time = int(service_duration.total_seconds())
                    in_service_status.save(update_fields=["is_active", "break_time"])

            instance.notify_user("update")

            start_queue_priority_routing_for_all_queues_in_project(instance.project)

        elif request.method == "GET":
            project_uuid = request.query_params.get("project")
            instance = get_object_or_404(
                ProjectPermission, project__uuid=project_uuid, user=request.user
            )

        return Response(
            dict(connection_status=instance.status), status=status.HTTP_200_OK
        )

    def delete(self, request):
        """Remove a project permission for the provided project/user pair."""
        permission = get_object_or_404(
            ProjectPermission,
            project_id=request.data["project"],
            user=request.data["user"],
        )
        permission.delete()
        return Response(
            status.HTTP_204_NO_CONTENT,
        )
