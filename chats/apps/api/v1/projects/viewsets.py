from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import (exceptions, mixins, pagination, permissions,
                            viewsets)
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.projects.serializers import ProjectSerializer
from chats.apps.projects.models import Project


class ProjectViewset(viewsets.ModelViewSet):
    queryset = Project.objects
    serializer_class = ProjectSerializer
    permission_classes = [
        IsAuthenticated,
    ]
