from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as filters

from chats.apps.sectors.models import Sector, SectorAuthorization


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
        return queryset
