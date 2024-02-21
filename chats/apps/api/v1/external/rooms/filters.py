from django_filters import rest_framework as filters

from chats.apps.rooms.models import Room


class RoomFilter(filters.FilterSet):
    class Meta:
        model = Room
        fields = ["urn", "is_active", "sector", "sector__name"]
