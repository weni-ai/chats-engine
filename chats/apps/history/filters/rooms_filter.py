from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import exceptions

from chats.apps.rooms.models import Room


class HistoryRoomFilter(filters.FilterSet):
    class Meta:
        model = Room
        fields = []

    contact = filters.CharFilter(
        field_name="contact",
        required=False,
        method="filter_contact",
        help_text=_("Contact's External ID"),
    )

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
    created_on = filters.DateFromToRangeFilter(
        field_name="created_on",
        required=False,
        help_text=_("Room created on"),
    )
    ended_at = filters.DateFromToRangeFilter(
        field_name="ended_at",
        required=False,
        help_text=_("Room ended at"),
    )

    def filter_project(self, queryset, name, value):
        qs = queryset
        user = self.request.user
        try:
            user_permission = user.project_permissions.get(project=value)
        except ObjectDoesNotExist:
            raise exceptions.APIException(
                detail="Access denied! Make sure you have the right permission to access this project"
            )

        queue_ids = user_permission.queue_ids

        contacts_blocklist = user_permission.project.history_contacts_blocklist
        if contacts_blocklist:
            qs = qs.exclude(contact__external_id__in=contacts_blocklist)

        return qs.filter(
            Q(queue__in=queue_ids) | Q(user=user, queue__sector__project=value),
            is_active=False,
            ended_at__isnull=False,
        )

    def filter_sector(self, queryset, name, value):
        return queryset.filter(queue__sector__uuid=value)

    def filter_tags(self, queryset, name, value):
        values = value.split(",")
        return queryset.filter(tags__name__in=values)

    def filter_contact(self, queryset, name, value):
        return queryset.filter(contact__external_id=value)
