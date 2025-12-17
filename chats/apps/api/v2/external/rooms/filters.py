from django_filters import rest_framework as filters

from chats.apps.rooms.models import Room


class ExternalRoomMetricsFilter(filters.FilterSet):
    sector = filters.CharFilter(
        field_name="queue__sector",
        required=False,
    )
    created_on__lte = filters.DateTimeFilter(field_name="created_on", lookup_expr="lte")
    created_on__gte = filters.DateTimeFilter(field_name="created_on", lookup_expr="gte")
    ended_at__gte = filters.DateTimeFilter(field_name="ended_at", lookup_expr="gte")
    ended_at__lte = filters.DateTimeFilter(field_name="ended_at", lookup_expr="lte")
    external_ids = filters.CharFilter(
        field_name="external_ids",
        required=False,
        method="filter_external_ids",
    )
    secondary_project = filters.CharFilter(
        field_name="secondary_project",
        required=False,
        method="filter_secondary_project",
    )

    class Meta:
        model = Room
        fields = [
            "urn",
            "is_active",
            "sector",
            "queue",
            "created_on__lte",
            "created_on__gte",
            "ended_at__lte",
            "ended_at__gte",
        ]

    def filter_external_ids(self, queryset, name, value):
        external_ids = value.split(",")

        return queryset.filter(contact__external_id__in=external_ids)

    def filter_secondary_project(self, queryset, name, value):
        return queryset.filter(queue__sector__secondary_project__uuid=value)
