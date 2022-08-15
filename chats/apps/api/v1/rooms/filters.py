from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room

from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag


class RoomFilter(filters.FilterSet):
    class Meta:
        model = Room
        fields = ["sector", "queue", "is_active"]

    sector = filters.CharFilter(
        field_name="sector",
        required=True,
        method="filter_sector",
        help_text=_("Sector's UUID"),
    )
    is_active = filters.BooleanFilter(
        field_name="is_active",
        required=False,
        method="filter_is_active",
        help_text=_("Is active?"),
    )

    def filter_sector(self, queryset, name, value):
        try:
            sector = Sector.objects.get(uuid=value)
            auth = sector.get_permission(self.request.user)
            auth.is_authorized
        except (Project.DoesNotExist, Sector.DoesNotExist, AttributeError):
            return SectorAuthorization.objects.none()
        return queryset.filter(sector__uuid=value)

    def filter_is_active(self, queryset, name, value):
        return queryset.filter(is_active=value)
