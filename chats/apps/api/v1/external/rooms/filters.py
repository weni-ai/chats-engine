from django.core.exceptions import ValidationError
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
        fields = ["urn", "is_active", "sector", "queue"]

    def filter_sector(self, queryset, name, value):
        sector_filter = Q(queue__sector__uuid__icontains=value) | Q(
            queue__sector__name__icontains=value
        )
        return queryset.filter(sector_filter)


class RoomMetricsFilter(RoomFilter):
    created_on__lte = filters.DateTimeFilter(field_name="created_on", lookup_expr="lte")
    created_on__gte = filters.DateTimeFilter(field_name="created_on", lookup_expr="gte")
    external_ids = filters.CharFilter(
        field_name="external_ids",
        required=False,
        method="filter_external_ids",
    )

    class Meta(RoomFilter.Meta):
        fields = RoomFilter.Meta.fields + ["created_on__lte", "created_on__gte"]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        created_on_lte = self.form.cleaned_data.get("created_on__lte")
        created_on_gte = self.form.cleaned_data.get("created_on__gte")

        if created_on_lte and created_on_gte and created_on_gte > created_on_lte:
            raise ValidationError(
                {"detail": "created_on__gte cannot be greater than created_on__lte"}
            )

        return queryset

    def filter_external_ids(self, queryset, name, value):
        external_ids = value.split(",")

        return queryset.filter(contact__external_id__in=external_ids)
