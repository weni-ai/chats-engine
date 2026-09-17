from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag


class SectorFilter(filters.FilterSet):
    class Meta:
        model = Sector
        fields = ["project"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Project ID"),
    )

    def filter_project(self, queryset, name, value):
        """
        Return sectors the user can access in the project: as project admin,
        sector manager, or agent in a queue belonging to the sector.
        """
        try:
            project = Project.objects.get(uuid=value)
        except Project.DoesNotExist:
            return queryset.none()
        user_sectors = project.get_sectors(user=self.request.user)
        return queryset.filter(pk__in=user_sectors.values("pk"))


class SectorAuthorizationFilter(filters.FilterSet):
    class Meta:
        model = SectorAuthorization
        fields = ["sector"]

    sector = filters.CharFilter(
        field_name="sector",
        required=False,
        method="filter_sector",
        help_text=_("Department UUID"),
    )

    status = filters.CharFilter(
        field_name="status",
        required=False,
        method="filter_status",
        help_text=_("User status"),
    )

    def filter_sector(self, queryset, name, value):
        return queryset.filter(sector__uuid=value)

    def filter_status(self, queryset, name, value):
        return queryset.filter(permission__status=value)


class SectorTagFilter(filters.FilterSet):
    class Meta:
        model = SectorTag
        fields = ["sector"]

    sector = filters.CharFilter(
        field_name="sector",
        required=False,
        method="filter_sector",
        help_text=_("Department UUID"),
    )

    queue = filters.CharFilter(
        field_name="queue",
        required=False,
        method="filter_queue",
        help_text=_("Queue UUID"),
    )

    search = filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
        required=False,
        help_text=_("Tag name"),
    )

    def filter_sector(self, queryset, name, value):
        try:
            sector = Sector.objects.get(uuid=value, is_deleted=False)
            auth = sector.get_permission(self.request.user)
            auth.is_manager(str(sector.pk))
        except (Project.DoesNotExist, Sector.DoesNotExist, AttributeError):
            return SectorTag.objects.none()
        return queryset.filter(sector__uuid=value)

    def filter_queue(self, queryset, name, value):
        try:
            sector = Sector.objects.get(queues__uuid=value, is_deleted=False)

            project_permission = sector.get_permission(self.request.user)

            if not project_permission.is_agent(queue=None, any_queue=True):
                return SectorTag.objects.none()

        except (Project.DoesNotExist, Sector.DoesNotExist, AttributeError):
            return SectorTag.objects.none()
        return queryset.filter(sector=sector)
