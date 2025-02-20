from django_filters import rest_framework as filters

from chats.apps.sectors.models import GroupSector


class GroupSectorFilter(filters.FilterSet):
    class Meta:
        model = GroupSector
        fields = ["project"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text="Project's ID",
    )

    def filter_project(self, queryset, name, value):
        return queryset.filter(project__uuid=value)
