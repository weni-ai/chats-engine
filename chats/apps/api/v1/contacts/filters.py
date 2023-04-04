from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from chats.apps.contacts.models import Contact
from chats.apps.rooms.models import Room
from django.db.models import Q, Max, OuterRef, Subquery


class ContactFilter(filters.FilterSet):
    class Meta:
        model = Contact
        fields = ["name", "email"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Projects's UUID"),
    )

    sector = filters.CharFilter(
        field_name="sector",
        required=False,
        method="filter_sector",
        help_text=_("Sector's UUID"),
    )

    tag = filters.CharFilter(
        required=False,
        method="filter_tags",
        help_text=_("Room Tags"),
    )
    created_on = filters.DateFromToRangeFilter()
    r_created_on = filters.DateFromToRangeFilter(
        field_name="rooms__created_on",
        required=False,
        help_text=_("Room created on"),
    )
    r_ended_at = filters.DateFromToRangeFilter(
        field_name="last_ended_at",
        required=False,
        help_text=_("Room ended at"),
    )

    def filter_project(self, queryset, name, value):
        qs = self.queryset
        user = self.request.user
        user_permission = user.project_permissions.get(project=value)
        queue_ids = user_permission.queue_ids

        subquery = Room.objects.filter(
            Q(queue_id__in=queue_ids) | Q(user=user, queue__sector__project=value),
            is_active=False,
            contact_id=OuterRef("uuid"),
        ).order_by("-ended_at")

        queryset = (
            qs.annotate(last_ended_at=Subquery(subquery.values("ended_at")[:1]))
            .filter(last_ended_at__isnull=False)
            .distinct()
        )
        return queryset

    def filter_sector(self, queryset, name, value):
        return queryset.filter(rooms__queue__sector__uuid=value)

    def filter_tags(self, queryset, name, value):
        values = value.split(",")
        return queryset.filter(rooms__tags__name__in=values)
