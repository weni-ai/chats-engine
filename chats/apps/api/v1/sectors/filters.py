from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from chats.apps.projects.models import Project

from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag
from django.db.models import Q


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
        user_role_filter = Q(
            Q(authorizations__permission__user=self.request.user)
            | Q(
                Q(project__permissions__user=self.request.user)
                & Q(project__permissions__role=1)
            )
        )
        try:
            queryset = queryset.filter(user_role_filter, project__uuid=value).distinct()
        except Sector.DoesNotExist:
            return Sector.objects.none()
        return queryset


class SectorAuthorizationFilter(filters.FilterSet):
    class Meta:
        model = SectorAuthorization
        fields = ["sector"]

    sector = filters.CharFilter(
        field_name="sector",
        required=False,
        method="filter_sector",
        help_text=_("Sector's UUID"),
    )

    def filter_sector(self, queryset, name, value):
        return queryset.filter(sector__uuid=value)


class SectorTagFilter(filters.FilterSet):
    class Meta:
        model = SectorTag
        fields = ["sector"]

    sector = filters.CharFilter(
        field_name="sector",
        required=False,
        method="filter_sector",
        help_text=_("Sector's UUID"),
    )

    queue = filters.CharFilter(
        field_name="queue",
        required=False,
        method="filter_queue",
        help_text=_("Queue's UUID"),
    )

    def filter_sector(self, queryset, name, value):
        try:
            sector = Sector.objects.get(uuid=value)
            auth = sector.get_permission(self.request.user)
            auth.is_manager(str(sector.pk))
        except (Project.DoesNotExist, Sector.DoesNotExist, AttributeError):
            return SectorTag.objects.none()
        return queryset.filter(sector__uuid=value)

    def filter_queue(self, queryset, name, value):
        try:
            sector = Sector.objects.get(queues__uuid=value)

            project_permission = sector.get_permission(self.request.user)

            if not project_permission.is_agent(value):
                return SectorTag.objects.none()

        except (Project.DoesNotExist, Sector.DoesNotExist, AttributeError):
            return SectorTag.objects.none()
        return queryset.filter(sector=sector)
