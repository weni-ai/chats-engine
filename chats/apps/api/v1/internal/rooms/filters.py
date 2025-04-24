from django.db.models import Q
from django_filters import rest_framework as filters

from chats.apps.rooms.models import Room


class RoomFilter(filters.FilterSet):
    created_on = filters.DateFromToRangeFilter(required=False)
    created_on__gte = filters.DateTimeFilter(
        required=False, field_name="created_on", lookup_expr="gte"
    )
    created_on__lte = filters.DateTimeFilter(
        required=False, field_name="created_on", lookup_expr="lte"
    )
    ended_at = filters.DateFromToRangeFilter(required=False)
    ended_at__gte = filters.DateTimeFilter(
        required=False, field_name="ended_at", lookup_expr="gte"
    )
    ended_at__lte = filters.DateTimeFilter(
        required=False, field_name="ended_at", lookup_expr="lte"
    )
    project = filters.CharFilter(
        required=True,
        method="filter_project",
    )
    sector = filters.BaseInFilter(
        field_name="queue__sector",
        required=False,
    )
    agent = filters.CharFilter(
        field_name="user",
        required=False,
    )
    attending = filters.BooleanFilter(
        required=False,
        method="filter_attending",
    )
    contact = filters.CharFilter(
        required=False,
        method="filter_contact",
    )

    tags = filters.CharFilter(
        required=False,
        method="filter_tags",
        help_text="Room Tags",
    )

    class Meta:
        model = Room
        fields = [
            "is_active",
            "queue",
        ]

    def filter_project(self, queryset, name, value):
        return queryset.filter(queue__sector__project=value)

    def filter_contact(self, queryset, name, value):
        return queryset.filter(
            Q(Q(contact__name__icontains=value) | Q(urn__icontains=value))
        )

    def filter_tags(self, queryset, name, value):
        values = value.split(",")
        return queryset.filter(tags__in=values)

    def filter_attending(self, queryset, name, value):
        return queryset.filter(user__isnull=not value)
