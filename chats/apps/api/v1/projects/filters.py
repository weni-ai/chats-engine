from django_filters import rest_framework as filters

from chats.apps.projects.models import FlowStart

from django.utils.translation import gettext_lazy as _


class FlowStartFilter(filters.FilterSet):
    created_on = filters.DateFromToRangeFilter()

    class Meta:
        model = FlowStart
        fields = ["created_on"]
