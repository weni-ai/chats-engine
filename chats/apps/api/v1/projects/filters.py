import django_filters

from chats.apps.projects.models import FlowStart
from datetime import timedelta


class FlowStartFilter(django_filters.FilterSet):
    start_time = django_filters.DateFilter(field_name="created_on", lookup_expr="gte")
    end_time = django_filters.DateFilter(field_name="created_on", lookup_expr="lte")

    class Meta:
        model = FlowStart
        fields = ["created_on"]

    def filter_queryset(self, queryset):
        start_time = self.form.cleaned_data.get("start_time")
        end_time = self.form.cleaned_data.get("end_time")

        if end_time:
            end_time = end_time + timedelta(days=1)
            queryset = queryset.filter(created_on__lt=end_time)

        if start_time:
            queryset = queryset.filter(created_on__gte=start_time)

        return queryset
