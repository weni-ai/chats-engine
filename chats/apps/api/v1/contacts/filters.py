from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from chats.apps.contacts.models import Contact


class ContactFilter(filters.FilterSet):
    class Meta:
        model = Contact
        fields = ["name", "email"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Projects's UUID"),
    )

    sector = filters.CharFilter(
        field_name="sector",
        required=False,
        method="filter_sector",
        help_text=_("Sector's UUID"),
    )

    tags = filters.MultipleChoiceFilter(conjoined=True)
    created_on = filters.DateRangeFilter()

    def filter_project(self, queryset, name, value):
        return queryset.filter(rooms__queue__sector__project__uuid=value)

    def filter_sector(self, queryset, name, value):
        return queryset.filter(rooms__queue__sector__uuid=value)

    # TODO: FILTER BY ROOM CLOSED DATE
    # room__created_on = filters.DateRangeFilter()
    # room_ended_at = filters.DateRangeFilter()
    # def filter_room_created_on(self, queryset, name, value):
    #     return queryset.filter(rooms__created_on=value)
