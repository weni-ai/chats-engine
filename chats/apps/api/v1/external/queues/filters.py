from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from chats.apps.queues.models import Queue


class QueueFlowFilter(filters.FilterSet):
    class Meta:
        model = Queue
        fields = ["sector", "name"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Project's ID"),
    )

    def filter_project(self, queryset, name, value):
        return queryset.filter(sector__project__uuid=value)
