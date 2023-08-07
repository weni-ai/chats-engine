from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from chats.apps.quickmessages.models import QuickMessage


class QuickMessageSectorFilter(filters.FilterSet):
    class Meta:
        model = QuickMessage
        fields = ["sector"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Project's UUID"),
    )

    def filter_project(self, queryset, name, value):
        return queryset.filter(sector__project=value)
