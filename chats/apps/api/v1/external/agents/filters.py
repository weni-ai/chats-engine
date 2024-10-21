from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from chats.apps.projects.models import ProjectPermission


class AgentFlowFilter(filters.FilterSet):
    class Meta:
        model = ProjectPermission
        fields = ["user", "role"]

    queue = filters.CharFilter(
        field_name="queue",
        required=False,
        method="filter_queue",
        help_text=_("Queue's ID"),
    )

    sector = filters.CharFilter(
        field_name="sector",
        required=False,
        method="filter_sector",
        help_text=_("Sector's ID"),
    )

    def filter_queue(self, queryset, name, value):
        return queryset.filter(queue_authorizations__queue=value)

    def filter_sector(self, queryset, name, value):
        return queryset.filter(sector_authorizations__sector=value)
