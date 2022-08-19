from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from chats.apps.api.v1.projects.serializers import ProjectSerializer
from chats.apps.projects.models import Project


class ProjectViewset(viewsets.ModelViewSet):
    queryset = Project.objects
    serializer_class = ProjectSerializer
    permission_classes = [
        IsAuthenticated,
    ]
    lookup_field = "uuid"
