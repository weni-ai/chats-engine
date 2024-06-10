from django.db.models import Q
from django_filters import rest_framework as filters

from chats.apps.rooms.models import Room


class RoomFilter(filters.FilterSet):
    created_on = filters.DateFromToRangeFilter(required=False)
    project = filters.CharFilter(
        required=True,
        method="filter_project",
    )
    sector = filters.CharFilter(
        field_name="sector",
        required=False,
        method="filter_sector",
    )
    agent = filters.CharFilter(
        field_name="user",
        required=False,
    )
    contact = filters.CharFilter(
        field_name="user",
        required=False,
        method="filter_contact",
    )

    tag = filters.CharFilter(
        required=False,
        method="filter_tags",
        help_text="Room Tags",
    )

    class Meta:
        model = Room
        fields = [
            "created_on",
            "is_active",
            "queue",
        ]

    def filter_project(self, queryset, name, value):
        return queryset.filter(queue__sector__project=value)

    def filter_sector(self, queryset, name, value):
        return queryset.filter(queue__sector=value)

    def filter_contact(self, queryset, name, value):
        return queryset.filter(
            Q(Q(contact__name__icontains=value) | Q(urn__icontains=value))
        )

    def filter_tags(self, queryset, name, value):
        values = value.split(",")
        return queryset.filter(tags__name__in=values)
