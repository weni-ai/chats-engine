from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room

from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag


class SectorFilter(filters.FilterSet):
    class Meta:
        model = Sector
        fields = ["project"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Project's ID"),
    )

    def filter_project(self, queryset, name, value):
        """
        Return sectors given a user, will check if the user is the project admin or
        if they have manager role on sectors inside the project
        """
        try:
            project = Project.objects.get(uuid=value)
            queryset = project.get_sectors(self.request.user)
        except (Project.DoesNotExist, Sector.DoesNotExist):
            return Sector.objects.none()
        return queryset


class SectorTagFilter(filters.FilterSet):
    class Meta:
        model = SectorTag
        fields = ["sector"]

    sector = filters.CharFilter(
        field_name="sector",
        required=True,
        method="filter_sector",
        help_text=_("Sector's UUID"),
    )

    def filter_sector(self, queryset, name, value):
        try:
            sector = Sector.objects.get(uuid=value)
            auth = sector.get_permission(self.request.user)
            auth.is_authorized
        except (Project.DoesNotExist, Sector.DoesNotExist, AttributeError):
            return SectorAuthorization.objects.none()
        return queryset.filter(sector__uuid=value)
