from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters

from chats.apps.rooms.models import Room

User = get_user_model()


class RoomFilter(filters.FilterSet):
    class Meta:
        model = Room
        fields = ["urn", "is_active"]
