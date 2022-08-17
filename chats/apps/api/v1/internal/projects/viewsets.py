from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, mixins, pagination, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.internal.projects import serializers
from chats.apps.projects.models import Project, ProjectPermission

# TODO: ADD THE INTERNALPERMISSION IN THESE ENDPOINTS


class ProjectViewset(viewsets.ModelViewSet):
    queryset = Project.objects
    serializer_class = serializers.ProjectSerializer
    permission_classes = [
        IsAuthenticated,
    ]


class ProjectAuthorizationViewset(viewsets.ModelViewSet):
    queryset = ProjectPermission.objects.all()
    serializer_class = serializers.ProjectAuthorizationSerializer
    permission_classes = [
        IsAuthenticated,
    ]
