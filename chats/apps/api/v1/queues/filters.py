from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from chats.apps.queues.models import Queue, QueueAuthorization


class QueueFilter(filters.FilterSet):
    class Meta:
        model = Queue
        fields = ["sector"]

    project = filters.CharFilter(
        field_name="project",
        required=False,
        method="filter_project",
        help_text=_("Project's UUID"),
    )

    def filter_project(self, queryset, name, value):
        return queryset.filter(sector__project=value)


class QueueAuthorizationFilter(filters.FilterSet):
    class Meta:
        model = QueueAuthorization
        fields = ["queue"]

    queue = filters.CharFilter(
        field_name="queue",
        required=True,
        method="filter_queue",
        help_text=_("queue's ID"),
    )

    status = filters.CharFilter(
        field_name="status",
        required=False,
        method="filter_status",
        help_text=_("User Status"),
    )

    def filter_status(self, queryset, name, value):
        return queryset.filter(permission__status=value)

    def filter_queue(self, queryset, name, value):
        return queryset.filter(queue=value)
