from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q


class GetPermission:
    def __init__(self, request) -> None:
        self.user = request.user
        self.data = request.data or request.query_params

        # Get the instance type and pk
        for key in ["project", "sector", "queue", "group_sector"]:
            pk = self.data.get(key, None)
            if pk:
                self.pk = pk
                self.queryset = getattr(self, key)
                break

    @property
    def project(self):
        return Q(project=self.pk)

    @property
    def sector(self):
        return Q(project__sectors=self.pk)

    @property
    def queue(self):
        return Q(project__sectors__queues=self.pk)

    @property
    def group_sector(self):
        return Q(project__group_sectors=self.pk)

    @property
    def permission(self):
        try:
            return self.user.project_permissions.get(self.queryset)
        except ObjectDoesNotExist:
            return None
