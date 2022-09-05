from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from chats.apps.api.v1.projects.serializers import ProjectSerializer
from chats.apps.api.v1.internal.projects.serializers import (
    ProjectPermissionReadSerializer,
)
from chats.apps.projects.models import Project, ProjectPermission

from chats.apps.api.v1.permissions import (
    IsProjectAdmin,
    IsSectorManager,
)


class ProjectViewset(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [
        IsAuthenticated,
    ]
    lookup_field = "uuid"


class ProjectPermissionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = ProjectPermission.objects.all()
    serializer_class = ProjectPermissionReadSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "project",
        "role"
    ]
    lookup_field = "uuid"

    def get_permissions(self):
        sector = self.request.query_params.get("sector")
        permission_classes = self.permission_classes

        if sector:
            permission_classes.append(IsSectorManager)
        else:
            permission_classes.append(IsProjectAdmin)
        return [permission() for permission in permission_classes]

