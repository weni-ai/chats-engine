from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.internal.projects import serializers
from chats.apps.projects.models import Project, ProjectPermission


class ProjectViewset(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = serializers.ProjectSerializer
    permission_classes = [IsAuthenticated, ModuleHasPermission]


class ProjectAuthorizationViewset(viewsets.ModelViewSet):
    queryset = ProjectPermission.objects.all()
    serializer_class = serializers.ProjectAuthorizationSerializer
    permission_classes = [IsAuthenticated, ModuleHasPermission]
