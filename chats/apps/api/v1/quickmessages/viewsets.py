from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from rest_framework import exceptions, viewsets
from rest_framework.permissions import IsAuthenticated

from chats.apps.api.v1.permissions import IsSectorManager
from chats.apps.api.v1.quickmessages.serializers import QuickMessageSerializer
from chats.apps.quickmessages.models import QuickMessage


class QuickMessageViewset(viewsets.ModelViewSet):
    queryset = QuickMessage.objects.exclude(sector__isnull=False)
    serializer_class = QuickMessageSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        if self.get_object().user == request.user:
            return super().update(request, *args, **kwargs)
        raise PermissionDenied

    def destroy(self, request, *args, **kwargs):
        if self.get_object().user == request.user:
            return super().destroy(request, *args, **kwargs)
        raise PermissionDenied

    def retrieve(self, request, *args, **kwargs):
        if self.get_object().user == request.user:
            return super().retrieve(request, *args, **kwargs)
        raise PermissionDenied

    def get_queryset(self, *args, **kwargs):
        return self.queryset.filter(user=self.request.user)


class SectorQuickMessageViewset(viewsets.ModelViewSet):
    queryset = QuickMessage.objects.all()
    serializer_class = QuickMessageSerializer

    def get_queryset(self, *args, **kwargs):
        if self.action == "list":
            try:
                project = self.request.GET.get("project")
                perm = self.request.user.project_permissions.get(project=project)
            except Exception as error:
                raise exceptions.APIException(
                    detail=f"You don't have permission to access this project. {type(error)}: {error}"
                )
            sectors = perm.get_sectors()
            return QuickMessage.objects.all().filter(
                sector__isnull=False, sector__in=sectors
            )
        return QuickMessage.objects.all().filter(sector__isnull=False)

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in ["create", "destroy", "partial_update", "update"]:
            permission_classes = (IsAuthenticated, IsSectorManager)
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)
