from django.db.models import Q
from django_filters import rest_framework as filters

from chats.apps.rooms.models import Room


class RoomFilter(filters.FilterSet):
    sector = filters.CharFilter(
        field_name="sector",
        required=False,
        method="filter_sector",
    )

    class Meta:
        model = Room
        fields = ["urn", "is_active", "sector"]

    def filter_sector(self, queryset, name, value):
        sector_filter = Q(queue__sector__uuid__icontains=value) | Q(
            queue__sector__name__icontains=value
        )
        return queryset.filter(sector_filter)
