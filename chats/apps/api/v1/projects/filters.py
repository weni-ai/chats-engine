from django_filters import rest_framework as filters

from chats.apps.projects.models import FlowStart
import django_filters
from chats.apps.projects.models import CustomStatusType
from django_filters.rest_framework import FilterSet


class FlowStartFilter(filters.FilterSet):
    created_on = filters.DateFromToRangeFilter()

    class Meta:
        model = FlowStart
        fields = ["created_on"]


class CustomStatusTypeFilterSet(FilterSet):
    project = django_filters.UUIDFilter(field_name="project_id")

    class Meta:
        model = CustomStatusType
        fields = ["project"]
