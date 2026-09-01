from django.db.models import Q
from django_filters import rest_framework as filters

from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.core.phone import build_urn_lookup_q, ninth_digit_search_enabled_from_request


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
    sector = filters.ModelMultipleChoiceFilter(
        required=False,
        field_name="queue__sector",
        queryset=Sector.objects.all(),
    )
    queue = filters.ModelMultipleChoiceFilter(
        required=False,
        field_name="queue",
        queryset=Queue.objects.all(),
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
    urn = filters.CharFilter(
        required=False,
        field_name="urn",
        lookup_expr="icontains",
    )
    contact_external_id = filters.CharFilter(
        required=False,
        field_name="contact__external_id",
    )

    tags = filters.CharFilter(
        required=False,
        method="filter_tags",
        help_text="Room Tags",
    )
    tag_name = filters.CharFilter(
        required=False,
        method="filter_tag_name",
        help_text="Tag name. Use with sector when the same name exists in more than one sector.",
    )
    protocol = filters.CharFilter(
        required=False,
        field_name="protocol",
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
        request = getattr(self, "request", None)
        ninth_digit_enabled = ninth_digit_search_enabled_from_request(request)
        return queryset.filter(
            Q(contact__name__unaccent__icontains=value)
            | build_urn_lookup_q(
                value,
                use_unaccent=True,
                ninth_digit_enabled=ninth_digit_enabled,
            )
        )

    def filter_tags(self, queryset, name, value):
        values = value.split(",")
        return queryset.filter(tags__in=values)

    def filter_tag_name(self, queryset, name, value):
        lookup = {"tags__name": value}
        sector = self.data.get("sector")
        if sector:
            lookup["tags__sector"] = sector
        return queryset.filter(**lookup).distinct()

    def filter_attending(self, queryset, name, value):
        return queryset.filter(user__isnull=not value)


class InternalProtocolRoomsFilter(filters.FilterSet):
    created_on__gte = filters.DateTimeFilter(
        required=False, field_name="created_on", lookup_expr="gte"
    )
    created_on__lte = filters.DateTimeFilter(
        required=False, field_name="created_on", lookup_expr="lte"
    )

    ended_at__gte = filters.DateTimeFilter(
        required=False, field_name="ended_at", lookup_expr="gte"
    )
    ended_at__lte = filters.DateTimeFilter(
        required=False, field_name="ended_at", lookup_expr="lte"
    )
    project = filters.CharFilter(
        required=True,
        field_name="queue__sector__project",
    )

    class Meta:
        model = Room
        fields = [
            "created_on__gte",
            "created_on__lte",
            "ended_at__gte",
            "ended_at__lte",
        ]
