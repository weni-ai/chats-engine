import django_filters
from django_filters import BaseInFilter, UUIDFilter

from chats.apps.rooms.models import Room


class UUIDInFilter(BaseInFilter, UUIDFilter):
    """Accepts comma-separated UUIDs: ?sector=uuid1,uuid2"""


class ExternalFinishedRoomsStatusFilter(django_filters.FilterSet):
    sector = UUIDInFilter(field_name="queue__sector__uuid", lookup_expr="in")
    queue = UUIDInFilter(field_name="queue__uuid", lookup_expr="in")
    tag = UUIDInFilter(field_name="tags__uuid", lookup_expr="in")
    agent = django_filters.CharFilter(field_name="user__email")

    class Meta:
        model = Room
        fields = []
