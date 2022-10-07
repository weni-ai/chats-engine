from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.api.v1.projects.serializers import ProjectSerializer
from chats.apps.api.v1.internal.projects.serializers import (
    ProjectPermissionReadSerializer,
    CheckAccessReadSerializer
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
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["project", "role", "status"]
    lookup_field = "uuid"

    def get_permissions(self):
        sector = self.request.query_params.get("sector")

        if sector:
            permission_classes = (IsAuthenticated, IsSectorManager)
        else:
            permission_classes = (IsAuthenticated, IsProjectAdmin)
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["GET"], url_name="verify_access")
    def verify_access(
        self, request, *args, **kwargs
    ):
        try:
            instance = ProjectPermission.objects.get(user=request.user, project=request.query_params["project"])
            serialized_data = CheckAccessReadSerializer(instance=instance)
        except (KeyError, ProjectPermission.DoesNotExist):
            return Response(
                {
                    "Detail": "You dont have permission in this project."
                },
                status.HTTP_401_UNAUTHORIZED,
            )
        return Response(serialized_data.data, status.HTTP_200_OK)
        

    @action(detail=False, methods=["PUT", "PATCH"], url_name="update_access")
    def update_access(
        self, request, *args, **kwargs
    ):
        try:
            instance = ProjectPermission.objects.get(user=request.user, project=request.query_params["project"])
            if instance.first_access == True:
                instance.first_access = False
                instance.save()
            serialized_data = CheckAccessReadSerializer(instance=instance)
        except (KeyError, ProjectPermission.DoesNotExist):
            return Response(
                {
                    "Detail": "You dont have permission in this project."
                },
                status.HTTP_401_UNAUTHORIZED,
            )
        return Response(serialized_data.data, status=status.HTTP_200_OK)