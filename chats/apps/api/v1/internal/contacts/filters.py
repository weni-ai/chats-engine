from django_filters import rest_framework as filters

from chats.apps.contacts.models import Contact


class RoomsContactsInternalFilter(filters.FilterSet):
    project = filters.CharFilter(required=True, method="filter_project")

    class Meta:
        model = Contact
        fields = []

    def filter_project(self, queryset, name, value):
        return queryset.filter(rooms__queue__sector__project__uuid=value).distinct()
