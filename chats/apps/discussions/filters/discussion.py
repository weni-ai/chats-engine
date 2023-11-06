from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from ..models import Discussion


class DiscussionFilter(filters.FilterSet):
    class Meta:
        model = Discussion
        fields = ["room", "is_active"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Projects's UUID"),
    )

    def filter_project(self, queryset, name, value):
        return queryset.filter(
            queue__sector__project=value
        )  # return only the discussions the user has access
