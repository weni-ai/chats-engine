from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from chats.apps.projects.models import Project

from chats.apps.sectorqueue.models import SectorQueue
from chats.apps.sectors.models import Sector


class SectorQueueFilter(filters.FilterSet):
    class Meta:
        model = SectorQueue
        fields = ["sector"]

    sector = filters.CharFilter(
        field_name="sector",
        required=True,
        method="filter_sector",
        help_text=_("sector's ID"),
    )

    def filter_sector(self, queryset, name, value):
        """
        Return sector given a user, will check if the user is the project admin or
        if they have manager role on sectors inside the project
        """
        try:
            sector = Project.objects.get(uuid=value)
            queryset = sector.get_sectors(self.request.user)
        except (Project.DoesNotExist, SectorQueue.DoesNotExist):
            return Sector.objects.none()
        return queryset
