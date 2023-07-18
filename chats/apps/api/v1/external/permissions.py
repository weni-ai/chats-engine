from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions

from chats.apps.projects.models import ProjectPermission


class IsAdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):  # pragma: no cover
        if view.action in ["list", "create"]:
            try:
                permission = request.auth
                project = permission.project

                validation = ValidatePermissionRequest(
                    request_data=request.data or request.query_params, project=project
                )

                return validation.is_valid
            except (AttributeError, IndexError, ProjectPermission.DoesNotExist):
                return False

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        try:
            permission = request.auth
            project = obj.project
        except ProjectPermission.DoesNotExist:
            return False
        return permission.project == project


LEVEL_NAME_MAPPING = {
    "project_uuid": "project",
    "project": "project",
    "sector_uuid": "pk",
    "sector": "pk",
    "queue_uuid": "queues",
    "queue": "queues",
    "room__uuid": "queues__rooms",
    "room": "queues__rooms",
}


class ValidatePermissionRequest:
    def __init__(self, request_data, project) -> None:
        self.project = project
        self.data = request_data
        self.queryset = {}

        # Get the instance type and pk
        for key in [
            "project",
            "sector",
            "queue",
            "project_uuid",
            "sector_uuid",
            "queue_uuid",
            "room__uuid",
            "room",
        ]:
            self.level_name = LEVEL_NAME_MAPPING[key]
            self.level_id = self.data.get(key, None)
            if self.level_name != "project" and self.level_id is not None:
                self.queryset = {self.level_name: self.level_id}
                break
            elif self.level_name == "project" and self.level_id is not None:
                break

    @property
    def is_valid(self):
        try:
            if self.level_name == "project":
                return str(self.project.pk) == self.level_id
            if self.queryset != {}:
                return self.project.sectors.filter(**self.queryset).exists()
        except ObjectDoesNotExist:
            return False
        return False
