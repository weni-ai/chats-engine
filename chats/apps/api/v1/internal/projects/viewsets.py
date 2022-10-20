from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.internal.projects import serializers
from chats.apps.projects.models import Project, ProjectPermission
from chats.core.views import persist_keycloak_user_by_email
from rest_framework import mixins, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404


class ProjectViewset(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = serializers.ProjectInternalSerializer
    permission_classes = [IsAuthenticated, ModuleHasPermission]
    lookup_field = "uuid"

    def create(self, request, *args, **kwargs):
        if settings.OIDC_ENABLED:
            user_email = request.data.get("user_email")
            if user_email is None:
                raise ValidationError("user_email is a required field!")
            persist_keycloak_user_by_email(user_email)

        return super().create(request, *args, **kwargs)


class ProjectPermissionViewset(viewsets.ModelViewSet):
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

    def create(self, request, *args, **kwargs):
        if settings.OIDC_ENABLED:
            user_email = request.data.get("user")
            persist_keycloak_user_by_email(user_email)

        return super().create(request, *args, **kwargs)

    def put(
        self, request, *args, **kwargs
    ):  # TODO: GAMBIARRA ALERT! MOVE THIS LOGIC TO THE SERIALIZER
        qs = self.queryset
        try:
            user_email = request.data["user"]
            role = request.data["role"]
            project = request.data["project"]

            permission = qs.get(user__email=user_email, project__uuid=project)
            permission.role = role
            permission.save()
        except (KeyError, ProjectPermission.DoesNotExist):
            return Response(
                {
                    "Detail": "The correct required fields are: user(str), role(int) and project(str)"
                },
                status.HTTP_400_BAD_REQUEST,
            )
        return Response({"Detail": "Updated"}, status.HTTP_200_OK)

    @action(detail=False, methods=["POST", "GET"], permission_classes=[IsAuthenticated])
    def status(self, request, *args, **kwargs):

        instance: ProjectPermission = None

        if request.method == "POST":
            project_uuid = request.data.get("project")
            instance = get_object_or_404(ProjectPermission, project__uuid=project_uuid, user=request.user)
            user_status = request.data.get("status")

            if user_status == "online":
                instance.status = "online"
                instance.save()
            elif user_status == "offline":
                instance.status = "offline"
                instance.save()

        elif request.method == "GET":
            project_uuid = request.query_params.get("project")
            instance = get_object_or_404(ProjectPermission, project__uuid=project_uuid, user=request.user)

        return Response(dict(connection_status=instance.status), status=status.HTTP_200_OK)
